"""Independent first-order mesh/Jacobian/host checks; no Abaqus solver.

NPZ keys for each part Rubber/Cords: <part>_coordinates (assembly/global Nx3),
<part>_nodeLabels (N); <part>_<type>_connectivity (node LABELS), and
<part>_<type>_elementLabels. Types: C3D8RH, C3D6H, C3D4H. Rubber host must
be C3D8RH. Requires Python 3, NumPy and SciPy; no Abaqus kernel imports.
"""
from pathlib import Path
import json
import argparse
import sys
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parent
SIGN=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],float)

def hex_shape(q):
    t=1+SIGN*q
    N=np.prod(t,axis=1)/8
    D=np.empty((8,3))
    for j in range(3):D[:,j]=SIGN[:,j]*np.prod(t[:,[k for k in range(3) if k!=j]],axis=1)/8
    return N,D

def wedge_shape(q):
    r,s,z=q;tri=np.array([1-r-s,r,s]);dt=np.array([[-1.,-1.],[1.,0.],[0.,1.]])
    N=np.r_[tri*(1-z)/2,tri*(1+z)/2];D=np.zeros((6,3))
    D[:3,:2]=dt*(1-z)/2;D[3:,:2]=dt*(1+z)/2;D[:3,2]=-tri/2;D[3:,2]=tri/2
    return N,D

def coordinates(data,name,typ):
    xyz=data[name+'_coordinates'];labels=data[name+'_nodeLabels'];conn=data[name+'_'+typ+'_connectivity']
    order=np.argsort(labels);idx=order[np.searchsorted(labels[order],conn)]
    assert np.array_equal(labels[idx],conn)
    return xyz[idx]

def quality(data):
    report={};g=1/np.sqrt(3)
    for name in ('Rubber','Cords'):
        for typ in ('C3D8RH','C3D6H','C3D4H'):
            if name+'_'+typ+'_connectivity' not in data:continue
            p=coordinates(data,name,typ)
            if typ=='C3D4H':
                det=np.linalg.det(np.stack((p[:,1]-p[:,0],p[:,2]-p[:,0],p[:,3]-p[:,0]),axis=2));volume=det/6;sample=det[:,None]
            else:
                shape=hex_shape if typ=='C3D8RH' else wedge_shape
                gp=[(x,y,z) for x in (-g,g) for y in (-g,g) for z in (-g,g)] if typ=='C3D8RH' else [(r,s,z) for r,s in ((1/6,1/6),(2/3,1/6),(1/6,2/3)) for z in (-g,g)]
                sample=np.column_stack([np.linalg.det(np.einsum('eni,nj->eij',p,shape(np.array(q))[1])) for q in gp])
                volume=sample.sum(axis=1)*(1 if typ=='C3D8RH' else 1/6)
                extra=SIGN if typ=='C3D8RH' else np.array([[r,s,z] for r,s in ((0,0),(1,0),(0,1),(1/3,1/3)) for z in (-1,0,1)])
                sample=np.column_stack([sample]+[np.linalg.det(np.einsum('eni,nj->eij',p,shape(q)[1])) for q in extra])
            bad=(~np.isfinite(sample)).any(axis=1)|(sample<=0).any(axis=1)|(volume<=0)|(~np.isfinite(volume))
            labels=data[name+'_'+typ+'_elementLabels']
            np.savetxt(ROOT/(name+'_'+typ+'_bad_jacobians.txt'),labels[bad],fmt='%d')
            report[name+'_'+typ]=dict(elements=len(p),minSampleJacobian=float(sample.min()),minVolume_mm3=float(volume.min()),totalVolume_mm3=float(volume.sum()),nonpositiveOrNonfiniteElements=int(bad.sum()),badLabels=labels[bad].tolist(),sampling='2x2x2 Gauss and 8 corners' if typ=='C3D8RH' else 'Exact linear tetrahedron' if typ=='C3D4H' else '6 Gauss and 12 corner/face points')
    return report

def containment(data, tolerance=.01):
    host=coordinates(data,'Rubber','C3D8RH');pts=data['Cords_coordinates'];tree=cKDTree(host.mean(axis=1))
    _,candidates=tree.query(pts,k=min(24,len(host)))
    candidates=np.asarray(candidates).reshape(len(pts),-1)
    maps=np.full(len(pts),-1,int);natural=np.full((len(pts),3),np.nan);residuals=np.full(len(pts),np.inf);outside=np.full(len(pts),np.inf)
    # Batched Newton inversion, evaluating multiple candidate elements per point.
    for column in range(candidates.shape[1]):
        pending=np.where(outside>1e-8)[0]
        if not len(pending):break
        ids=candidates[pending,column];p=host[ids];target=pts[pending];q=np.zeros((len(pending),3))
        for iteration in range(15):
            t=1+q[:,None,:]*SIGN[None,:,:];N=np.prod(t,axis=2)/8;D=np.empty((len(q),8,3))
            for j in range(3):D[:,:,j]=SIGN[None,:,j]*np.prod(t[:,:,[k for k in range(3) if k!=j]],axis=2)/8
            err=np.einsum('en,eni->ei',N,p)-target;J=np.einsum('eni,enj->eij',p,D)
            delta=np.linalg.solve(J,err[...,None])[...,0];q-=delta
            if np.max(np.abs(delta))<1e-10:break
        t=1+q[:,None,:]*SIGN[None,:,:];N=np.prod(t,axis=2)/8
        res=np.linalg.norm(np.einsum('en,eni->ei',N,p)-target,axis=1)
        qc=np.clip(q,-1,1);Nc=np.prod(1+qc[:,None,:]*SIGN[None,:,:],axis=2)/8
        ext=np.linalg.norm(np.einsum('en,eni->ei',Nc,p)-target,axis=1)
        valid=np.isfinite(ext)&np.isfinite(res)&(res<1e-7)
        improve=valid&(ext<outside[pending]);where=pending[improve]
        maps[where]=ids[improve];natural[where]=q[improve];residuals[where]=res[improve];outside[where]=ext[improve]
    passed=(maps>=0)&(outside<=tolerance)
    np.savez_compressed(ROOT/'host_node_map.npz',cordNodeLabels=data['Cords_nodeLabels'],hostElementLabels=data['Rubber_C3D8RH_elementLabels'][np.maximum(maps,0)],natural=natural,residual_mm=residuals,outsideDistance_mm=outside,passed=passed)
    return dict(nodesChecked=len(pts),passed=int(passed.sum()),failed=int((~passed).sum()),maxOutsideDistance_mm=float(outside.max()),maxInverseResidual_mm=float(residuals.max()),exteriorTolerance_mm=tolerance,candidateElementsPerNode=candidates.shape[1],method='C3D8 reference-coordinate inverse trilinear mapping; distance to clipped natural coordinates',solverEmbeddingValidated=False,failedNodeLabels=data['Cords_nodeLabels'][~passed].tolist())

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--exterior-tolerance',type=float,default=.01)
    args=parser.parse_args()
    if not np.isfinite(args.exterior_tolerance) or args.exterior_tolerance<0:parser.error('Exterior tolerance must be finite and nonnegative')
    ROOT=args.output_dir.resolve();ROOT.mkdir(parents=True,exist_ok=True)
    data=np.load(args.mesh);report=quality(data)
    (ROOT/'independent_mesh_check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='badLabels'} for k,v in report.items()},indent=2))
    hosts=containment(data,args.exterior_tolerance);(ROOT/'host_containment_check.json').write_text(json.dumps(hosts,indent=2));print(json.dumps({k:v for k,v in hosts.items() if k!='failedNodeLabels'},indent=2))
    sys.exit(1 if hosts['failed'] or any(v['nonpositiveOrNonfiniteElements'] for v in report.values()) else 0)
