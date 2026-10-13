"""Small analytical fixtures; does not open or change Abaqus models."""
from pathlib import Path
import tempfile
import numpy as np
import check_mesh as check


def fixture(shift=0.):
    host=(check.SIGN+1)/2
    cord=(check.SIGN+1)/10+.4
    cord[:,0]+=shift
    data={}
    for name,xyz in [('Rubber',host),('Cords',cord)]:
        data[name+'_coordinates']=xyz
        data[name+'_nodeLabels']=np.arange(101,109)
        data[name+'_C3D8RH_connectivity']=np.arange(101,109)[None,:]
        data[name+'_C3D8RH_elementLabels']=np.array([901])
    return data


def main():
    with tempfile.TemporaryDirectory(prefix='abaqus-mesh-check-') as directory:
        check.ROOT=Path(directory)
        data=fixture();q=check.quality(data)
        assert abs(q['Rubber_C3D8RH']['totalVolume_mm3']-1)<1e-12
        assert q['Rubber_C3D8RH']['nonpositiveOrNonfiniteElements']==0
        assert check.containment(data)['passed']==8
        assert check.containment(fixture(2.))['failed']==8
        inverted=fixture();inverted['Cords_C3D8RH_connectivity']=inverted['Cords_C3D8RH_connectivity'][:,[1,0,3,2,5,4,7,6]]
        assert check.quality(inverted)['Cords_C3D8RH']['nonpositiveOrNonfiniteElements']==1
    print('PASS: analytical unit volume, one-host containment, outside rejection, inverted element detection')


if __name__=='__main__':main()
