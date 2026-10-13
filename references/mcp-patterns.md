# 实时 MCP 操作示例与 API 陷阱

以下为已在 Abaqus 2022/Python 2.7 实时内核使用的方法。执行代码通过 Abaqus MCP 的 run_python / execute_script；示例中的对象和路径要在当前会话核对后绑定，不默认存在。

## 分阶段执行

先读取当前状态，再创建独立模型。不要为了检验技能重跑用户已有模型。

```python
import os, sys
from abaqus import mdb, session
result = {'python': sys.version, 'cwd': os.getcwd(),
          'mdb': mdb.pathName, 'models': list(mdb.models.keys())}
```

写文件/创建 Job 前切换到独立输出目录。分批创建帘线时返回创建数与总数；失败后检查实际已完成数量，清理失败的单个构造对象，再从该批次断点继续。不要把一段长脚本整体重跑。

## 拉压开关属于 Elastic

```python
mat.Elastic(table=((E, nu),))
mat.elastic.setValues(noCompression=ON)  # 拉伸分支
mat.elastic.setValues(noTension=ON)      # 压缩分支；不同材料对象
```

Material 没有 `NoCompression()` / `NoTension()` 方法。这只是材料参数保存/实体分支设置，不能证明原 rebar 多轴实体行为已经标定，也不替代分支叠加。

## 复杂端部的局部切分

保存修复前检查点；先确定目标帘线 cell 和靠端部的切分位置。不要对整个 cp.cells 批量切全部帘线。

```python
from abaqusConstants import XZPLANE
datum = cp.DatumPlaneByPrincipalPlane(principalPlane=XZPLANE,
                                     offset=y_cut)
cp.PartitionCellByDatumPlane(cells=target_cells,
                            datumPlane=cp.datums[datum.id])
```

`PartitionCellByPlanePointNormal` 的 normal 参数需要 Abaqus 支持的方向对象；不要把任意三元向量直接塞给该 API。主平面不适合当前几何时，先以 datum point/axis/plane 构造局部法向平面，再分割指定 cells。

切分会重编号 cells。后续用重新定位的点、集合或检查过的新索引，而非沿用修复前的固定索引。所选点应在 cell 内部；必要时用该 cell 网格节点均值辅助定位，随后检查是否确实选中了目标实体。

## 扫掠及端部回退

```python
cp.setElementType(regions=(cp.cells,), elemTypes=(
    mesh.ElemType(elemCode=C3D8RH, elemLibrary=STANDARD),
    mesh.ElemType(elemCode=C3D6H, elemLibrary=STANDARD),
    mesh.ElemType(elemCode=C3D4H, elemLibrary=STANDARD)))
cp.setMeshControls(regions=body_cells, elemShape=HEX,
                   technique=SWEEP, algorithm=ADVANCING_FRONT)
```

HEX 比 HEX_DOMINATED 更适合尝试消除主体内部的楔形网格；失败后先分区，再按当前用户授权范围仅对无法扫掠的小端部回退。改变控制后核验所有 cells 已有网格，以及真实单元类型。

## 导出和质量检查

```python
a.regenerate()  # 必须早于读取新网格实例节点
coords = [n.coordinates for n in a.instances['Rubber-Host'].nodes]
labels = [n.label for n in a.instances['Rubber-Host'].nodes]
conn = [[n.label for n in e.getNodes()] for e in hp.elements]
q = cp.verifyMeshQuality(criterion=ANALYSIS_CHECKS)
```

MeshElement.connectivity 可能是部件节点索引，不是标签；用 getNodes() 取标签。若实例节点为空或数量不匹配，不继续独立检查，先再生并重新导出。

SectionAssignment.region 在该版本中可为区域描述 tuple；用其名称核对 part.sets 中实际 cell 覆盖，不调用 `.region.cells`。

离线 NumPy 2 的批量线性方程求解使用 `solve(J, rhs[..., None])[..., 0]`，避免二维 rhs 被解释为矩阵导致维度错误。奇异/非有限映射须记录为检查失败，不能忽略。

## 实时显示

默认只改变实时视口显示，不保存图片：

```python
vp.setValues(displayedObject=a)
vp.assemblyDisplay.setValues(mesh=ON)
vp.assemblyDisplay.geometryOptions.setValues(
    datumAxes=OFF, datumPlanes=OFF, datumPoints=OFF,
    datumCoordSystems=OFF)
vp.forceRefresh()
```

datum 显示开关属于 assemblyDisplay.geometryOptions，不属于 assemblyDisplay.setValues。用户要求截图时，每种显示刷新后用单独 MCP 调用导出，避免多次切换/导出在一段脚本中捕获到同一旧画面。
