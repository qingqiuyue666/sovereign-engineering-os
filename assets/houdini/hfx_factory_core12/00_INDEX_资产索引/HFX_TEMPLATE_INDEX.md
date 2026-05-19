# Houdini HFX Template Index

## 01_运动拖尾_速度线残影

### HFX_001_Energy_Trail_Basic
用途：
- 能量拖尾
- 速度线基础
- 人物运动残影基础
- 通用 motion path FX

状态：
- v001 自动生成完成
- 可打开 HIP 调整路径、宽度、噪声、颜色
- 后续升级：粒子火花、宽度渐变、发光材质、速度属性

### HFX_002_Slash_Trail_Curve
用途：
- 刀光
- 武器拖尾
- 动漫斩击弧线
- 高速挥动轨迹

状态：
- v001 自动生成完成
- 可打开 HIP 调整弧线、宽度、火花、颜色、缩放
- 后续升级：动画显隐、碰撞火花、motion-vector pass、发光材质

---

## 02_烟尘雾气_扬尘环境雾

### HFX_003_Footstep_Dust_Impact
用途：
- 脚步扬尘
- 落地尘
- 地面接触尘
- 小型冲击尘

状态：
- v001 自动生成完成
- 可打开 HIP 调整脚底接触范围、粒子数量、速度、VDB 密度
- 后续升级：帧触发发射、风场、碎石粒子、阴影 pass

### HFX_004_Ground_Dust_Ring
用途：
- 地面冲击尘环
- 踏地冲击波
- 落地扩散尘
- radial dust layer

状态：
- v001 自动生成完成
- 可打开 HIP 调整半径、扩散速度、VDB 体积、扰动
- 后续升级：动画扩散、debris 粒子、density falloff、wind advection

---

## 03_火焰爆炸_火球浓烟

### HFX_005_Small_Pyro_Burst
用途：
- 小型火爆
- 火球基础层
- 烟火喷发
- impact ignition

状态：
- v001 自动生成完成
- 当前是程序化 VDB/体积源基础，不是真正 Pyro Solver 高级模拟
- 后续升级：真实 Pyro Solver、fuel/temperature 场、Karma/Redshift 材质、阴影 pass

---

## 04_破碎裂地_碎石坍塌

### HFX_006_Ground_Crack_Debris
用途：
- 地裂
- 小型碎石飞溅
- 踏地破坏层
- debris burst

状态：
- v001 自动生成完成
- 当前是裂纹线 + 碎石分布基础，不是真正 RBD 高级模拟
- 后续升级：真实 RBD、fracture chunks、dust interaction、velocity/age attributes

---

## 05_能量魔法_电弧传送门

### HFX_007_Lightning_Arc_Basic
用途：
- 电弧
- 能量连接
- 魔法闪电
- 传送门边缘电流

状态：
- v001 自动生成完成
- 可打开 HIP 调整主电弧、分支、噪声、宽度、颜色
- 后续升级：帧闪烁、端点火花、发光材质、camera-facing glow

### HFX_008_Energy_Shockwave
用途：
- 能量冲击波
- 圆环爆发
- 魔法冲击环
- hit-frame energy ring

状态：
- v001 自动生成完成
- 可打开 HIP 调整半径、噪声、光环、径向 streak
- 后续升级：动画扩散、alpha-card glow、ID groups、材质 emission 控制

---

## 当前第一批模板结论

已完成：
- HFX_001 Energy Trail
- HFX_002 Slash Trail
- HFX_003 Footstep Dust
- HFX_004 Ground Dust Ring
- HFX_005 Small Pyro Burst
- HFX_006 Ground Crack Debris
- HFX_007 Lightning Arc
- HFX_008 Energy Shockwave

已经补上的分类：
- 01_运动拖尾_速度线残影
- 02_烟尘雾气_扬尘环境雾
- 03_火焰爆炸_火球浓烟
- 04_破碎裂地_碎石坍塌
- 05_能量魔法_电弧传送门

后续待做：
- 06_流体液体_水黏液黑液
- 07_布料柔体_披风破布
- 08_毛发羽毛_生物特效

注意：
这些是 v001 自动模板骨架，不是最终电影级版本。
下一阶段应打开 HIP 做视觉检查，再升级 v002。
