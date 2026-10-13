# Belt2 MCP 模型与 2D 来源文件

下载本目录中的 `Belt2_MCP_model_and_2D_source.zip` 并解压。

- `belt2/`：最终网格 CAE、无网格几何 CAE、审阅 INP、网格/host 数组及检查资料。
- `source_2d/`：`2D.inp`、`2D.odb`、`material.lib`、`PARAMETER.INP`；INP 所需 include 文件一并保留。
- `PACKAGE_MANIFEST.json`：包内文件大小与 SHA256。

模型只完成几何和网格阶段，未加载、未 datacheck、未求解。压缩包不含 3D ODB、历史检查点和预览图片。旧建模报告/旧 manifest 中的预览图片路径只是原本地交付记录，本包不包含这些图片；包内文件以 PACKAGE_MANIFEST.json 为准。

橡胶为单个整体实体；两根复杂帘线端部切分后主体恢复 C3D8RH。仍保留 3908 个帘线形状警告。默认在 Abaqus 中实时查看，不生成预览图。

公开上传范围由用户明确指定为 Belt2 最终成果与必要的 2D 来源资料。
