# SplatCraft 📸→🫧→🎮

**Photo → 3D Gaussian Splatting → VRChat Asset**

一键将实物照片转化为 VRChat 可用的 3D 资产。

## 两条路径

| | Splat Mode | Mesh Mode |
|---|---|---|
| **原理** | 直接渲染高斯泼溅 | 转Mesh+物理碰撞 |
| **效果** | 照片级真实感 | 传统3D模型 |
| **物理** | ❌ | ✅ 凸分解碰撞体 |
| **用途** | 世界道具、场景 | Avatar、可交互道具 |
| **VRChat插件** | [VRChatGaussianSplatting](https://github.com/MichaelMoroz/VRChatGaussianSplatting) | VRChat SDK |

## 快速开始

```bash
# 安装
pip install -e ".[gui]"

# 系统检查
splatcraft check

# 构建（从照片到VRChat资产）
splatcraft build ./my_photos -o ./output

# 启动Web UI
splatcraft gui
```

## Pipeline

```
📸 照片输入 (≥3张)
    ↓
🔍 COLMAP 预处理 (相机位姿估计)
    ↓
🎯 3DGS 训练 (Nerfstudio/OpenSplat)
    ↓
┌─────────────────┬──────────────────┐
│ .ply 泼溅文件    │ SuGaR Mesh提取    │
│ (VRChat世界)     │ ↓                 │
│                  │ 减面优化           │
│                  │ ↓                 │
│                  │ 凸分解碰撞体       │
│                  │ (Unity/VRChat)    │
└─────────────────┴──────────────────┘
    ↓
📦 VRChat Package (README + 资产 + Unity脚本)
```

## 硬件要求

- **NVIDIA GPU** ≥ 8GB VRAM (24GB+ 推荐)
- **CUDA** 11.8+
- **RAM** ≥ 16GB
- 推荐：RTX 3090/4090/5090

## CLI 参数

```bash
splatcraft build <input_dir> [options]

Options:
  -o, --output PATH       输出目录 (default: output)
  -m, --mode MODE         splat | mesh | both (default: both)
  -b, --backend BACKEND   nerfstudio | opensplat | original
  -i, --iterations N      训练轮次 (default: 30000)
  -p, --platform PLAT     pc | quest (default: pc)
  -r, --rank RANK         excellent | good | medium | poor
  --high-poly             高精度Mesh提取
  --no-physics            跳过碰撞体生成
  -v, --verbose           详细日志
```

## 依赖

| 组件 | 用途 | 安装 |
|------|------|------|
| Nerfstudio | 3DGS训练 | `pip install nerfstudio` |
| SuGaR | Mesh提取 | [github.com/Anttwo/SuGaR](https://github.com/Anttwo/SuGaR) |
| CoACD | 碰撞体 | `pip install coacd` |
| Blender | Mesh优化(可选) | [blender.org](https://blender.org) |
| VRChatGaussianSplatting | .ply渲染 | [github.com/MichaelMoroz/VRChatGaussianSplatting](https://github.com/MichaelMoroz/VRChatGaussianSplatting) |

## 一键安装

```bash
bash scripts/install_deps.sh
```

## 为什么不用现成工具？

| 工具 | 问题 |
|------|------|
| KIRI Engine | 云服务，收费，不可定制 |
| Polycam | 同上 |
| Meshy/Tripo3D | 输出Mesh，不支持3DGS |
| 手动Nerfstudio+SuGaR | 碎片化，需要手动串6个步骤 |

SplatCraft 把所有步骤串成一条命令，自动处理中间格式转换、性能验证、Unity脚本生成。

## License

MIT
