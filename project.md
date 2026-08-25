
::: dark-mode
:::

# WarpSAC: Towards the Pinnacle of Scalable Off-Policy RL by Rethinking Exploration and Exploitation

::: author
Zihao Wu^1^, Hongyao Tang^1^, Yi Ma^2^, Huizhong Song^2^, Pengyi Li^1^, Yifu Yuan^1^, Fei Ni^3^, Jinyi Liu^1^, Wei Wei^2^, Jianrong Wang^1^, Yan Zheng^1^, and Jianye Hao^1^
:::

::: institution
^1^Tianjin University · ^2^Shanxi University · ^3^Imperial College London
:::

::: button
[<i class="fa fa-file-pdf-o" aria-hidden="true"></i> Paper](assets/warpsac-paper.pdf)
[<i class="fa fa-youtube-play" aria-hidden="true"></i> Demo](#demo)
[<i class="fa fa-github" aria-hidden="true"></i> Code](https://github.com/wzhhasadream/warprl)
[<i class="fa fa-chart-bar" aria-hidden="true"></i> Results](#results)
:::

## Demo

::: row
@[video](assets/mp4/warpsac.mp4)
(a) WarpSAC on Unitree G1 Flat after approximately 35 minutes of training.

@[video](assets/mp4/flashsac.mp4)
(b) FlashSAC on Unitree G1 Flat after approximately 55 minutes of training.
:::


## Abstract

WarpSAC is an off-policy reinforcement-learning framework for both CPU-scale and GPU-parallel simulation. It provides JAX and PyTorch backends and supports continuous-control benchmarks spanning MuJoCo, IsaacLab, MJLab, ManiSkill, and related suites.

Our implementation examines how exploration, replay prioritization, parameter normalization, and scalable updates interact across data-limited and data-abundant training regimes.

![Unitree G1 Flat sample-efficiency and wall-clock learning curves](assets/png/unitree_g1_flat_learning_curves.png)

::: caption
**Figure 1.** Unitree G1 Flat learning curves measured by environment steps and training wall-clock time. WarpSAC reaches strong performance with fewer environment steps and less wall time than FlashSAC.
:::

## Method

WarpSAC is a controlled extension of FlashSAC that separates replay-side exploitation from network-side stabilization. Its main replay component, **Sample Weight Decay (SWD)**, assigns each transition an age-dependent sampling weight. Recent, policy-relevant data are sampled more often, while older transitions retain a nonzero weight for coverage. SWD changes only the minibatch distribution; it introduces no auxiliary network, Bellman target, or loss term.

Parameter projection normalization is selected according to replay coverage. It renormalizes network parameters after each optimizer step, constraining the effective function class and reducing unstable value extrapolation. CPU-scale training has narrower replay coverage, so WarpSAC-L keeps normalization enabled together with clipped double-Q targets. GPU-parallel simulation collects broad, rapidly refreshed data; in this data-abundant regime, the same constraint can restrict value fitting, so WarpSAC-A disables normalization and uses the less conservative single-Q variant.

| Profile | Configuration |
| --- | --- |
| **WarpSAC-L** | Data-limited CPU scale: SWD, Norm ON, clipped double-Q |
| **WarpSAC-A** | Data-abundant GPU scale: SWD, Norm OFF, single-Q |
| **Automatic profiles** | Defaults are resolved from the environment type and replay regime |


![Combined CPU-scale and GPU-parallel learning curves](assets/png/combined_normalized_cpu_gpu_envstep_curves.png)

::: caption
**Figure 2.** Combined CPU-scale and GPU-parallel learning curves. We recommend WarpSAC-L for CPU-scale training and WarpSAC-A for GPU-parallel training.
:::

## Results

### CPU-Scale vs. GPU-Parallel

CPU-scale and GPU-parallel workloads present distinct replay regimes. We therefore report them separately, using WarpSAC-L for data-limited CPU-scale environments and WarpSAC-A for data-abundant GPU-parallel environments.

![CPU-scale learning curves in four data-limited environments](assets/png/cpu_norm_on_four_panel_curves.png)

::: caption
**Figure 3.** CPU-scale learning curves across MuJoCo, DMC, HumanoidBench, and MyoSuite. WarpSAC-L is evaluated in the data-limited regime with parameter normalization enabled.
:::

GPU-parallel simulation produces broad, rapidly refreshed replay data. The following results evaluate WarpSAC-A in IsaacLab, ManiSkill, MJLab, and Playground.

![GPU-parallel learning curves in four data-abundant environments](assets/png/gpu_single_q_four_panel_curves.png)

::: caption
**Figure 4.** GPU-parallel learning curves across IsaacLab, ManiSkill, MJLab, and Playground. WarpSAC-A is evaluated in the data-abundant regime without parameter normalization.
:::

### Normalization × Network Capacity

We next examine how the profile-dependent normalization choice interacts with network capacity. The ablations below cover GPU-parallel Playground training and CPU-scale training separately.

![Network-capacity ablation in GPU-parallel training](assets/png/bar_playground_scale_ablation_combined.png)

::: caption
**Figure 5.** Playground network-capacity ablation comparing WarpSAC variants and FlashSAC in GPU-parallel training.
:::

The CPU-scale ablation evaluates the corresponding WarpSAC-L configuration under narrower replay coverage.

![Network-capacity ablation in CPU-scale training](assets/png/cpu_scale_ablation_bars.png)

::: caption
**Figure 6.** CPU-scale network-capacity ablation comparing WarpSAC-L and FlashSAC.
:::

## Task Demo Videos


::: row
@[video](assets/mp4/Unitree-A2-Flat.mp4)
Unitree A2 Flat locomotion.
@[video](assets/mp4/Unitree-G1-Flat.mp4)
Unitree G1 Flat locomotion.
:::


::: row
@[video](assets/mp4/Unitree-Go2-Flat.mp4)
Unitree Go2 Flat locomotion.

@[video](assets/mp4/Unitree-H1_2-Flat.mp4)
Unitree H1-2 Flat locomotion.
:::


## Getting started

We provide an easy-to-use implementation of **WarpSAC** for scalable off-policy reinforcement-learning research in robotics. The codebase supports JAX and PyTorch backends, automatic environment-specific configuration, CPU and CUDA replay, and the Unitree G1 MJLab sim-to-real setup.

Please visit the [WarpSAC GitHub repository](https://github.com/wzhhasadream/warprl) for installation instructions, training commands, environment integrations, and configuration options.

## Citation

Use the following entry when citing the project. Update the author and venue fields when the paper metadata is final.

```bibtex
@article{warpsac,
  title  = {WarpSAC: Towards the Pinnacle of Scalable Off-Policy Reinforcement Learning},
  author = {Wu, Zihao and Tang, Hongyao and Ma, Yi and Song, Huizhong and Li, Pengyi and Yuan, Yifu and Ni, Fei and Liu, Jinyi and Wei, Wei and Wang, Jianrong and Zheng, Yan and Hao, Jianye},
  year   = {2026}
}
```
