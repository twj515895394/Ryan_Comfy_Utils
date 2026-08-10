# MiniMax H3 提示词模板

模板用于组织内容，不要求逐字照抄。先完成模式判断和素材映射，再选择最接近的模板。最终 prompt 默认使用官方字段；对白、歌词、字幕、Logo 和 UI 文案保留用户原文。

## 1. T2VA：纯文生

### 适用条件

没有参考素材，从文本构造完整视听时间线。

### 结构

```text
integrated_multimodal_description: [Shot 1] 视觉媒介与整体风格，景别、主体位置、环境和初始状态。主体完成动作，镜头以明确的运动类型、幅度和速度跟随；对白或画内声音写在对应动作旁。 [Shot 2] At 00:SS.mmm, the camera cuts to ...

overall_soundscape: 全片环境声、动作声和非语言人声，1–4 句；不要重复对白和歌曲。

non_diegetic_music: 角色听不到的背景音乐；无音乐使用 N/A。
```

## 2. I2VA：首帧向后发展

### 适用条件

用户明确指定图片为首帧。

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] 从 <Picture 1> 的主体、构图、服装、空间和光线开始，保持身份和关键关系；随后描述动作起始、连续发展、镜头运动和结果。

overall_soundscape: ...

non_diegetic_music: ...
```

不要把单张普通参考图默认写成 I2VA。

## 3. FL2VA：首尾帧补间

### 适用条件

用户明确指定首帧和尾帧。

```text
How the reference pictures align with the target video — Picture 1 (from Shot 1) aligns with the 0.00-second mark of the target video; Picture 2 (from Shot 1) aligns with the 8.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] 从 Picture 1 的起始状态开始，描述主体移动、姿态变化、物体状态、镜头和光线的连续变化，逐步缩小与 Picture 2 的差异，并在视频末端到达 Picture 2 的构图和状态。

overall_soundscape: ...

non_diegetic_music: ...
```

默认使用单一连续镜头；只有用户明确要求多镜头时才改变结构。

## 4. L2VA：向尾帧收敛

### 适用条件

用户明确指定尾帧，没有指定首帧。

```text
How the reference pictures align with the target video — Picture 1 (from [Shot N]) aligns with the 8.00-second mark of the target video.

integrated_multimodal_description: [Shot 1] 从与 Picture 1 相容的前置状态开始，描述动作、物体状态、镜头和空间关系逐步向尾帧收敛；最后一个 Shot 到达 Picture 1 的主体位置、姿态、构图、光线和细节。

overall_soundscape: ...

non_diegetic_music: ...
```

不要把尾帧图片放在 Shot 1，也不要让最后状态只停留在“类似尾帧”。

## 5. Ref2VA：全参考

### 适用条件

多张图片、视频、音频共同参与生成，或素材需要分别指定人物、场景、动作、运镜和声音角色。

```text
subject_definitions: <Subject 1> 是来自 <Picture 1> 的人物，只锁定脸部、发型和服装轮廓。<Subject 2> 是来自 <Picture 2> 的场景，只锁定空间结构和光线。<Video 1> 是动作参考，不复制其中人物身份。<Audio 1> 仅作为音色参考，不复制原始音频信号。

summary: [reference generation] 目标视频使用 <Subject 1>、<Subject 2>、<Video 1> 和 <Audio 1> 的指定关系完成新的事件。

retention_analysis: <Subject 1> (appears in [Shot 1]): fully_preserved - ...; <Subject 2>: partially_preserved - ...; <Video 1> (action rhythm): weak_reference - ...; <Audio 1>: reference - ...

detailed_description: 先用一至两句建立整体视觉媒介和风格，再按播放顺序描述每个 Shot 的构图、主体、环境、动作、镜头、声音和引用标签。每个说话人使用稳定的 (S1)/(S2)，对白使用 <d>[Language] 原文</d>。

overall_soundscape: ...

non_diegetic_music: ...
```

## 6. 视频编辑

```text
subject_definitions: <Video 1> 是待编辑原视频；<Subject 1> 是需要替换或修改的目标；<Picture 1> 是新对象参考，只锁定外形、颜色和材质。

summary: [video editing] The target video is an edited version of <Video 1>.

retention_analysis: <Video 1> (camera, timing and unmodified content): fully_preserved - ...; <Subject 1>: attribute_transfer - ...

detailed_description: 修改项：...；修改范围：...；保持原镜头、动作、时序、空间遮挡、光线和未修改内容；禁止改变未列出的身份、服装、表情、文字和背景关系。

overall_soundscape: 保留或替换的环境声说明。

non_diegetic_music: 保留、替换或 N/A。
```

## 7. 视频续接

```text
subject_definitions: <Video 1> 是续接来源视频；<Subject 1> 是原视频结尾仍在场的主体。

summary: [video continuation] The target video continues from the final valid state of <Video 1>.

retention_analysis: <Video 1> (final state, camera and spatial continuity): fully_preserved - ...

detailed_description: 从 <Video 1> 的最后有效状态开始，不重复已经完成的动作；新动作从现有姿态、镜头、光线和声音自然展开。

overall_soundscape: ...

non_diegetic_music: ...
```

## 8. 音频替换与参考

```text
subject_definitions: <Video 1> 是原视频；<Audio 1> 是完整/片段音频复用来源，或仅作为音色、节奏参考。

summary: [video editing + audio reuse] ... 或 [video editing + audio reference] ...

retention_analysis: <Audio 1>: fully_copy / partially_copy / reference - 明确复制或参考的时间段、轨道和内容。

detailed_description: 明确说话人、台词原文、画内/画外关系、开始时间、口型和跨镜连续性；不要把音色参考误写成原始信号复制。

overall_soundscape: ...

non_diegetic_music: ...
```

## 9. 复杂多镜头通用约束

每个 Shot 至少包含：景别、主体位置、当前状态、动作、镜头运动、切换方式、台词/声音和与前后 Shot 的连续性。单一 Shot 不堆叠互相独立的主要动作；动作必须有可观察的起始状态和结束状态。
