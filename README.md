# Abaqus MCP Belt Submodel

基于 Codex 的实时 Abaqus MCP 带束层子模型 skill：整体橡胶、实体帘线、Embedded 连接、C3D8RH 主体网格、复杂端部切分和独立网格检查。

## 使用

将本仓库克隆或复制为 `~/.codex/skills/abaqus-mcp-belt-submodel/`，使其中的 `SKILL.md` 位于该目录顶层。在 Codex 中调用：

> 使用 $abaqus-mcp-belt-submodel，通过 Abaqus MCP 建立第二带束层子模型并划网格。保留曲率，橡胶整体化，帘线与橡胶主体使用 C3D8RH。复杂端部先切分，默认不生成预览图；不加载、不求解。

需要已连接的 Abaqus MCP 和实时 CAE 会话。建模操作在 Abaqus 内核执行；离线检查脚本使用 Python 3、NumPy 和 SciPy，不需要导入 Abaqus。

## 内容

- [SKILL.md](SKILL.md)：工作流、范围、验收和用户默认偏好。
- [MCP 操作示例](references/mcp-patterns.md)：分阶段内核操作、端部切分、Elastic 拉压开关、实例坐标导出及 API 陷阱。
- [Belt2 案例](references/belt2-case.md)：实际参数、橡胶整体化、切分前后统计与验证边界。
- [网格检查脚本](scripts/check_mesh.py)：C3D8RH/C3D6H/C3D4H Jacobian、体积和 C3D8 host 包含性检查。

```text
python scripts/check_mesh.py --mesh /path/to/mesh_arrays.npz --output-dir /path/to/checks --exterior-tolerance 0.01
python scripts/test_check_mesh.py
```

NPZ 输入需包含 Rubber/Cords 的实例全局参考坐标、节点标签以及各单元类型的节点标签连接和单元标签，键名格式在脚本开头说明。检查结果有不合格项时返回非零退出码；运行错误也不能当作通过。

此流程只在用户请求的范围内工作；建模或网格请求不自动运行 datacheck/求解。几何包含性检查不等于 solver Embedded 验证，案例也不是材料或网格敏感性验证。用户另行授权公开上传的仿真示例放入 `examples/`，不作为 skill 自动执行的输入或默认模板。
