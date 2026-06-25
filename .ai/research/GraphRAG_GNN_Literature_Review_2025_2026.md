# GraphRAG与GNN结合应用研究文献综述（2025–2026）

> **调研日期**: 2026年6月13日
> **调研范围**: arXiv、ACL、SIGIR、ICML、PAKDD 等主要学术平台
> **时间窗口**: 2025年1月 – 2026年6月
> **关键词**: GraphRAG, Graph Neural Networks, Knowledge Graph, Retrieval-Augmented Generation

---

## 摘要

图检索增强生成（Graph Retrieval-Augmented Generation, GraphRAG）与图神经网络（Graph Neural Networks, GNN）的结合是2025–2026年间知识增强大语言模型领域最活跃的研究方向之一。本综述系统梳理了该时期内40余篇代表性论文，从 **GNN作为图编码器增强GraphRAG**、**图结构原生集成到LLM**、**智能体驱动的图推理**、**领域应用**、**轻量化与效率优化** 以及 **综述与框架** 六个维度进行分析，揭示了该领域的核心趋势与未来方向。

---

## 一、GNN作为图编码器增强GraphRAG检索

### 1.1 核心思想

传统GraphRAG（如Microsoft GraphRAG）主要依赖社区检测和文本索引构建知识图谱，但在子图编码和多跳推理方面存在局限。GNN凭借其消息传递机制，能够将图拓扑结构信息编码为低维表示，从而增强检索的语义理解能力。

### 1.2 代表性工作

#### (1) Ex-GraphRAG: Interpretable Evidence Routing for Graph-Augmented LLMs
- **作者**: Yoav Kor Sade, Arvindh Arun, Rishi Puri, Steffen Staab, Maya Bechler-Speicher
- **日期**: 2026年5月
- **arXiv**: [2605.21994](https://arxiv.org/abs/2605.21994)
- **核心贡献**:
  - 提出 **Ex-GraphRAG**，用 **多元图神经加性网络（M-GNAN）** 替代传统黑盒GNN编码器
  - M-GNAN能够对编码器输出进行 **精确的节点级分解**，无需事后近似
  - 在STaRK-Prime基准上，可解释编码器达到与黑盒模型相当的性能
  - 揭示了 **语义-结构不匹配** 现象：主导编码器输出的节点在检索子图中结构上不连通，由低归因中间节点连接；移除这些中间节点导致多跳QA性能下降高达28%
- **意义**: 首次证明GNN编码器在GraphRAG中的可解释性不仅可行，而且能揭示传统方法无法发现的检索缺陷

#### (2) Query-Aware Graph Neural Networks for Enhanced Retrieval-Augmented Generation
- **作者**: Vibhor Agrawal, Fay Wang, Rishi Puri
- **日期**: 2025年7月
- **arXiv**: [2508.05647](https://arxiv.org/abs/2508.05647)
- **核心贡献**:
  - 提出 **查询感知的GNN** 架构，将查询语义注入图神经网络的消息传递过程
  - 通过查询条件化的注意力机制，使GNN能够根据当前问题动态调整子图编码策略
  - 在多个知识图谱QA基准上取得显著改进
- **意义**: 解决了传统GNN编码器对查询无感知的问题，实现了检索与推理的深度耦合

#### (3) Question-Adaptive Graph Learning for Multi-hop Retrieval Augmented Generation
- **作者**: Yuchen Yan, Peiyan Zhang, Zhihua Liu, Hao Wang, Yatao Bian, Weiming Li, Xiaoshuai Hao
- **日期**: 2025年10月（**SIGIR 2026 录用**）
- **arXiv**: [2510.11541](https://arxiv.org/abs/2510.11541)
- **核心贡献**:
  - 提出 **Multi-L KG** 知识图谱结构，建模多层信息级别以全面理解多跳问题
  - 设计 **Quest-GNN**，使用问题引导的层内/层间消息传递机制
  - 提出两种合成数据预训练策略增强鲁棒性
  - 在高跳数问题上取得高达 **33.8%** 的性能提升
- **意义**: 将GNN的消息传递与问题语义深度结合，显著提升了复杂多跳推理能力

#### (4) TCAR-Gen: Temporal Graph Retrieval with Evidence Fusion for Knowledge-Grounded Generation
- **作者**: Sidra Nasir, Muhammad Noman Zahid, Rizwan Ahmed Khan
- **日期**: 2026年4月
- **arXiv**: [2606.00029](https://arxiv.org/abs/2606.00029)
- **核心贡献**:
  - 提出 **TCAR-Gen** 框架，结合 **查询条件化GNN、时序证据融合和链式树推理**
  - 在Victorian Crime Diaries基准上实现0.3738 Recall@5，超越Vanilla RAG、Temporal RAG、GraphRAG-C和GraphRAG-T
  - 消融实验证明上下文图、时序惩罚机制和查询条件化是关键组件
- **意义**: 首次将时序建模与GNN编码深度融合到GraphRAG中，拓展了图检索的时间维度

#### (5) STAR: Semantic-Tuned and Tail-Adaptive Retriever for Graph-Augmented Generation
- **作者**: Shuai Li, Chen Huang, Duanyu Feng, Wenqiang Lei, See-Kiong Ng
- **日期**: 2026年4月
- **arXiv**: [2605.18765](https://arxiv.org/abs/2605.18765)
- **核心贡献**:
  - 发现图检索中两种被忽视的偏差：**语义捷径偏差（Semantic Shortcut Bias）** 和 **长尾路径偏差（Long-Tail Path Bias）**
  - 提出 **STAR**，整合令牌级交互学习（交叉注意力+硬路径挖掘）和路径加权对比学习
  - 在所有基准上平均检索性能提升1.8%，QA性能提升2.2%
- **意义**: 深入分析了GNN在图检索中的偏差问题，提出了系统性解决方案

---

## 二、图结构原生集成到LLM

### 2.1 核心思想

与将GNN作为外部编码器不同，另一类研究致力于将图结构直接注入LLM的注意力机制或表示空间，消除GNN-LLM之间的语义鸿沟。

### 2.2 代表性工作

#### (1) Teaching LLMs to See Graphs: Unifying Text and Structural Reasoning (GTLM)
- **作者**: Dario Vajda
- **日期**: 2026年5月
- **arXiv**: [2605.10247](https://arxiv.org/abs/2605.10247)
- **核心贡献**:
  - 提出 **Graph Transformer Language Model (GTLM)**，通过注入 **图感知注意力偏置** 让预训练LLM直接处理图拓扑
  - 仅增加 **0.015%** 的额外参数，保持节点置换等变性和向后兼容性
  - 1B参数的GTLM在文本属性图任务上匹配或超越7B参数的最先进模型
  - GTLM注意力头隐式学习模拟消息传递，为图算法推理提供机制解释
- **意义**: 消除了GNN压缩为单一令牌的语义瓶颈，为下一代GraphRAG奠定基础

#### (2) Neural Graph Matching Improves Retrieval Augmented Generation in Molecular Machine Learning (MARASON)
- **作者**: Runzhong Wang, Rui-Xi Wang, Mrunali Manjrekar, Connor W. Coley
- **日期**: 2025年2月（**ICML 2025 录用**）
- **arXiv**: [2502.17874](https://arxiv.org/abs/2502.17874)
- **核心贡献**:
  - 提出 **MARASON** 模型，将神经图匹配与碎片化神经网络结合用于质谱模拟
  - 通过建模两个结构图之间的节点和边亲和力，实现噪声鲁棒的端到端学习
  - Top-1准确率达到28%，相比非检索SOTA（19%）提升约47%
- **意义**: 首次将图匹配引入分子领域的RAG，证明了结构对齐在检索增强中的价值

#### (3) From Node2Vec to GPT-based GraphRAG: Scientific Impact Prediction
- **作者**: Adilson Vital Jr., Filipi N. Silva, Diego R. Amancio
- **日期**: 2026年5月
- **arXiv**: [2605.18410](https://arxiv.org/abs/2605.18410)
- **核心贡献**:
  - 统一框架比较图方法（Node2Vec）和LLM方法（GPT-based GraphRAG）在科学影响力预测中的表现
  - 有监督设置下，有向引用图嵌入+文本嵌入组合达到0.84-0.85 AUC
  - GPT-based GraphRAG达到0.87 AUC，但图邻域上下文并不总能改善结果
  - 发现简单LLM基线有时与GraphRAG表现相当
- **意义**: 提供了图模型与LLM检索增强的系统性对比，揭示了GraphRAG的适用边界

---

## 三、智能体驱动的图推理与GraphRAG

### 3.1 核心思想

2025–2026年，"智能体（Agent）+图"成为新兴范式。将LLM作为图节点上的自主代理，或通过多智能体协作实现图遍历和推理。

### 3.2 代表性工作

#### (1) ReaGAN: Node-as-Agent-Reasoning Graph Agentic Network
- **作者**: Minghao Guo, Xi Zhu, Haochen Xue, Chong Zhang, Shuhang Lin, Jingyuan Huang, Ziyi Ye, Yongfeng Zhang
- **日期**: 2025年8月
- **arXiv**: [2508.00429](https://arxiv.org/abs/2508.00429)
- **核心贡献**:
  - 提出 **ReaGAN**，每个节点作为独立代理，基于内部记忆自主规划下一步动作
  - 利用RAG使节点能够访问语义相关内容，建立图中的全局关系
  - 使用冻结LLM骨干网络，在少样本上下文学习设置下实现竞争性性能，无需微调
  - 解决了传统GNN中节点信息量不平衡和固定聚合方案的局限
- **意义**: 开创了"节点即代理"的图推理范式，将RAG从检索工具升级为图推理的全局语义桥梁

#### (2) MemGraphRAG: Memory-based Multi-Agent System for Graph Retrieval-Augmented Generation
- **作者**: Chuanjie Wu, Zhishang Xiang, Yunbo Tang, Zerui Chen, Qinggang Zhang, Jinsong Su
- **日期**: 2026年5月
- **arXiv**: [2606.00610](https://arxiv.org/abs/2606.00610)
- **核心贡献**:
  - 将记忆机制引入多智能体GraphRAG系统
  - 多个智能体协作进行图检索、推理和记忆更新
  - 实现了动态知识积累和检索优化
- **意义**: 将多智能体协作与GraphRAG结合，实现了更灵活的图知识管理

#### (3) SAGE: A Self-Evolving Agentic Graph-Memory Engine
- **作者**: Juntong Wang, Haoyue Zhao, Guanghui Pan, Xiyuan Wang, Yanbo Wang, Qiyan Deng, Muhan Zhang
- **日期**: 2026年5月
- **arXiv**: [2605.12061](https://arxiv.org/abs/2605.12061)
- **核心贡献**:
  - 提出 **SAGE**，将图记忆建模为动态长期记忆基底
  - 包含 **Memory Writer**（从交互历史增量构建结构化图记忆）和 **Memory Reader**（基于图基础模型的检索与反馈）
  - 读者-写者反馈循环使记忆系统能够自我进化
  - 两轮自进化后在多跳QA上取得最佳平均排名；零样本开放域迁移在NQ上达到82.5/91.6 Recall@2/5
  - 反馈驱动训练改善了幻觉诊断指标
- **意义**: 将GraphRAG从静态检索中间件升级为自进化的智能记忆系统

#### (4) DOTRAG: Retrieval-Time Reasoning Along Paths
- **作者**: Larnell Moore, Naihao Deng, Rada Mihalcea, Farnaz Jahanbakhsh
- **日期**: 2026年4月
- **arXiv**: [2605.18760](https://arxiv.org/abs/2605.18760)
- **核心贡献**:
  - 提出 **DotRAG**，免训练的GraphRAG框架，将检索重新定义为路径上的推理过程
  - 引入 **Division of Thought (DOT)** 抽象，将检索分解为局部搜索空间并自适应调整搜索策略
  - 生成查询条件化约束指导图探索、剪枝无关区域、发现关系路径
  - 在MetaQA和UltraDomain基准上达到SOTA
- **意义**: 将检索过程本身转化为推理，突破了传统"先检索后推理"的范式

---

## 四、轻量化与效率优化

### 4.1 核心思想

GraphRAG的计算成本（特别是LLM token消耗）是实际部署的主要障碍。2025–2026年出现了一系列轻量化方案。

### 4.2 代表性工作

#### (1) EHRAG: Bridging Semantic Gaps in Lightweight GraphRAG via Hybrid Hypergraph Construction and Retrieval
- **作者**: Yifan Song, Xingjian Tao, Zhicheng Yang, Yihong Luo, Jing Tang
- **日期**: 2026年4月（**ACL 2026 Findings 录用**）
- **arXiv**: [2604.17458](https://arxiv.org/abs/2604.17458)
- **核心贡献**:
  - 提出 **EHRAG**，构建同时编码结构和语义关系的超图
  - 结构超边来自句子级共现，语义超边通过实体文本嵌入聚类
  - 检索使用结构-语义混合扩散+主题感知评分+个性化PageRank精炼
  - 线性索引复杂度，图构建阶段 **零token消耗**
  - 在四个基准数据集上超越现有基线
- **意义**: 在保持轻量化的同时解决了NER-based GraphRAG的语义连接缺失问题

#### (2) Beyond Chunk-Local Extraction: Cross-Chunk Graph Augmentation for GraphRAG (CrossAug)
- **作者**: Jiaming Zhang, Yibo Zhao, Jing Yu, Jianxiang Yu, Xiang Li
- **日期**: 2026年5月
- **arXiv**: [2605.28004](https://arxiv.org/abs/2605.28004)
- **核心贡献**:
  - 提出 **CrossAug**，一种GNN引导的跨块图增强方法
  - 丰富GraphRAG索引的跨块关系结构
  - 突破了传统GraphRAG仅在单个文本块内提取实体关系的限制
- **意义**: 用GNN指导GraphRAG的索引构建，而非仅用于检索阶段

#### (3) GraphRAG on Consumer Hardware: Benchmarking Local LLMs for Healthcare EHR Schema Retrieval
- **作者**: Peter Fernandes, Ria Kanjilal
- **日期**: 2026年5月
- **arXiv**: [2605.20815](https://arxiv.org/abs/2605.20815)
- **核心贡献**:
  - 在消费级硬件上基准测试本地LLM的GraphRAG能力
  - 聚焦医疗电子健康记录（EHR）模式检索场景
  - 评估了不同规模本地模型的性能-成本权衡
- **意义**: 推动GraphRAG从云端向边缘设备的民主化部署

#### (4) AtomicRAG: Atom-Entity Graphs for Retrieval-Augmented Generation
- **作者**: Yanning Hou, Duanyang Yuan, Sihang Zhou, Xiaoshu Chen, Ke Liang, Siwei Wang, Xinwang Liu, Jian Huang
- **日期**: 2026年2月
- **arXiv**: [2604.20844](https://arxiv.org/abs/2604.20844)
- **核心贡献**:
  - 提出 **Atom-Entity Graph**，以知识原子（单个自包含事实单元）而非粗粒度文本块存储知识
  - 实体边仅指示关系存在性，降低对关系抽取错误的敏感性
  - 结合个性化PageRank与相关性过滤
  - 在五个公共基准上超越强RAG基线
- **意义**: 重新定义了GraphRAG的知识粒度，提升了检索灵活性和推理鲁棒性

---

## 五、领域应用

### 5.1 医疗健康

#### (1) CuraView: Multi-Agent Framework for Medical Hallucination Detection with GraphRAG
- **作者**: Severin Ye, Xiao Kong, Xiaopeng He, Guangsu Yan, Dongsuk Oh
- **日期**: 2026年5月
- **arXiv**: [2605.03476](https://arxiv.org/abs/2605.03476)
- **核心贡献**:
  - 多智能体框架，利用GraphRAG增强知识验证检测医疗幻觉
  - 通过图结构化的医学知识验证LLM生成内容的事实一致性
- **意义**: 将GraphRAG应用于LLM可靠性保障，特别是在高风险的医疗领域

#### (2) GraphRAG on Consumer Hardware for Healthcare EHR
- 见第四节(3)，同时具有医疗领域应用价值

### 5.2 法律

#### LegalGraphRAG: Multi-Agent Graph Retrieval-Augmented Generation for Reliable Legal Reasoning
- **作者**: Zerui Chen, Qinggang Zhang, Zhishang Xiang, Zhimin Wei, Linfeng Gao, Xiao Huang, Zhihong Zhang, Jinsong Su
- **日期**: 2026年5月
- **arXiv**: [2605.28120](https://arxiv.org/abs/2605.28120)
- **核心贡献**:
  - 多智能体GraphRAG框架专门针对法律推理
  - 通过图结构化的法律知识提升推理的可靠性和可追溯性
- **意义**: 法律领域对推理可解释性要求极高，GraphRAG+GNN的图路径天然提供推理证据链

### 5.3 金融

#### Agentic GraphRAG: Navigating Unstructured Financial Data with Collaborative AI
- **作者**: Arthur Capozzi, Dirk Helbing
- **日期**: 2026年4月
- **arXiv**: [2605.18770](https://arxiv.org/abs/2605.18770)
- **核心贡献**:
  - 智能体GraphRAG框架处理非结构化金融数据
  - 多智能体协作导航复杂的金融知识图谱
- **意义**: 金融数据的高度关联性使其成为GraphRAG的理想应用场景

### 5.4 农业与生物

#### Knowledge Reasoning of LLMs Integrating Graph-Structured Information for Pest and Disease Control
- **作者**: Siyu Li, Chenwei Song, Wan Zhou, Xinyi Liu
- **日期**: 2025年12月
- **arXiv**: [2512.21837](https://arxiv.org/abs/2512.21837)
- **核心贡献**:
  - 基于GraphRAG框架，使用GNN学习烟草病虫害知识图谱的节点表示
  - 将图结构化信息整合到LLM知识推理中
- **意义**: 展示了GraphRAG+GNN在垂直领域知识推理中的实际应用价值

### 5.5 电信标准

#### SEM-RAG: Structure-Preserving Multimodal Graph Compilation and Entropy-Guided Retrieval
- **作者**: Yuzhi Yang, Lina Bariah, Yuhuan Lu, Hang Zou, Mérouane Debbah
- **日期**: 2026年5月
- **arXiv**: [2605.08997](https://arxiv.org/abs/2605.08997)
- **核心贡献**:
  - 结构保持的多模态图编译+熵引导检索
  - 针对电信标准文档的GraphRAG应用
- **意义**: 将GraphRAG扩展到技术标准领域，处理高度结构化的规范文档

---

## 六、综述与框架

#### (1) LLMs+Graphs: Toward Graph-Native, Synergistic AI Systems
- **作者**: Arijit Khan, Longxu Sun, Xin Huang
- **日期**: 2026年6月（**PAKDD 2026 Tutorial**）
- **arXiv**: [2606.11560](https://arxiv.org/abs/2606.11560)
- **核心贡献**:
  - 系统梳理了三大互补协同方向：
    1. **LLM + 图计算** 增强检索和推理
    2. **LLM-KG双向集成**：LLM辅助KG构建，KG约束LLM生成
    3. **AI Agent + 图算法** 增强规划和决策
  - 提出"图原生AI系统"愿景
  - 强调混合LLM-GNN流水线的重要性
- **意义**: 该领域最全面的综述之一，为研究者提供统一视角

#### (2) Are LLMs Better GNN Helpers? Rethinking Robust Graph Learning under Deficiencies with Iterative Refinement (RoGRAD)
- **作者**: Zhaoyan Wang, Zheng Gao, Arogya Kharel, In-Young Ko
- **日期**: 2025年10月
- **arXiv**: [2510.01910](https://arxiv.org/abs/2510.01910)
- **核心贡献**:
  - 首个系统性基准，比较传统GNN与LLM增强方法在多种图缺陷下的表现
  - 发现LLM增强并非始终优于传统方法
  - 提出 **RoGRAD**，利用RAG进行图增强的迭代对比学习范式
  - 平均性能提升高达82.43%
- **意义**: 挑战了"LLM增强必然更好"的假设，为GraphRAG+GNN的实际部署提供了重要参考

#### (3) GraphInfer-Bench: Benchmarking LLM's Inference Capability on Graphs
- **作者**: Zhuoyi Peng, Jingzhou Jiang, Hanlin Gu, Lixin Fan, Yi Yang
- **日期**: 2026年6月
- **arXiv**: [2606.11562](https://arxiv.org/abs/2606.11562)
- **核心贡献**:
  - 评估LLM在图推理任务上的能力
  - 发现"普通GNN在多数任务上匹配或超越最强LLM"
- **意义**: 为GNN在GraphRAG中的不可替代性提供了实证支持

---

## 七、研究趋势与关键发现

### 7.1 六大趋势

| 趋势 | 描述 | 代表论文 |
|------|------|----------|
| **GNN编码器可解释化** | 从黑盒GNN转向可解释的图编码器，实现证据路由审计 | Ex-GraphRAG |
| **查询条件化图学习** | 将查询语义注入GNN消息传递，实现检索-推理深度耦合 | Quest-GNN, STAR, TCAR-Gen |
| **图结构原生集成** | 将图拓扑直接注入LLM注意力机制，消除GNN-LLM语义鸿沟 | GTLM |
| **智能体化图推理** | 每个节点/实体作为自主代理，RAG提供全局语义 | ReaGAN, SAGE, MemGraphRAG |
| **轻量化与效率** | 零token图构建、超图、原子级知识粒度 | EHRAG, AtomicRAG, CrossAug |
| **自进化记忆** | 图记忆系统通过反馈循环自我优化 | SAGE |

### 7.2 关键发现

1. **GNN不可替代性**: GraphInfer-Bench表明，在结构化推理任务上，普通GNN仍匹配或超越LLM，证明GNN在GraphRAG中具有不可替代的价值

2. **语义-结构不匹配**: Ex-GraphRAG揭示的语义重要性与结构连通性由不同节点集控制的现象，对GraphRAG系统设计有深远影响

3. **LLM增强的局限性**: RoGRAD发现LLM增强并非始终优于传统GNN，需谨慎评估适用场景

4. **GNN模拟消息传递**: GTLM证明LLM注意力头能隐式学习模拟GNN消息传递，为统一架构提供理论基础

5. **简单基线的竞争力**: 在某些场景下（如科学影响力预测），简单LLM基线与GraphRAG表现相当，需审慎评估GraphRAG的增量价值

### 7.3 技术路线图

```
                    GraphRAG + GNN 技术演进路线
                    ================================

2024: Microsoft GraphRAG 发布
      ├── 社区检测 + 文本索引
      └── 朴素检索 (无GNN)

2025 H1: GNN增强检索
      ├── 查询感知GNN (Query-Aware GNN)
      ├── 图匹配RAG (MARASON, ICML 2025)
      └── 多跳图学习 (Quest-GNN)

2025 H2: 智能体化与效率
      ├── 节点即代理 (ReaGAN)
      ├── 迭代RAG增强 (RoGRAD)
      └── 时序图检索 (TCAR-Gen)

2026 H1: 原生集成与自进化
      ├── 图结构注入LLM (GTLM, 0.015%参数)
      ├── 可解释证据路由 (Ex-GraphRAG)
      ├── 自进化图记忆 (SAGE)
      ├── 跨块图增强 (CrossAug)
      └── 多智能体GraphRAG (MemGraphRAG, LegalGraphRAG)

未来方向:
      ├── 统一图-语言架构 (消除GNN/LLM边界)
      ├── 实时动态图更新
      ├── 多模态GraphRAG (文本+图+视觉)
      └── 端到端可训练GraphRAG流水线
```

---

## 八、论文索引

| # | 论文标题 | 作者 | 日期 | arXiv/会议 | 类别 |
|---|---------|------|------|-----------|------|
| 1 | Ex-GraphRAG: Interpretable Evidence Routing | Kor Sade et al. | 2026.05 | 2605.21994 | 可解释GNN编码 |
| 2 | Query-Aware GNN for Enhanced RAG | Agrawal et al. | 2025.07 | 2508.05647 | 查询感知GNN |
| 3 | Question-Adaptive Graph Learning (Quest-GNN) | Yan et al. | 2025.10 | 2510.11541 / SIGIR 2026 | 多跳图学习 |
| 4 | TCAR-Gen: Temporal Graph Retrieval | Nasir et al. | 2026.04 | 2606.00029 | 时序图检索 |
| 5 | STAR: Semantic-Tuned Retriever | Li et al. | 2026.04 | 2605.18765 | 检索偏差修正 |
| 6 | GTLM: Teaching LLMs to See Graphs | Vajda | 2026.05 | 2605.10247 | 图结构原生集成 |
| 7 | MARASON: Neural Graph Matching for RAG | Wang et al. | 2025.02 | 2502.17874 / ICML 2025 | 分子图匹配 |
| 8 | Node2Vec to GPT-based GraphRAG | Vital Jr. et al. | 2026.05 | 2605.18410 | 图vs.LLM对比 |
| 9 | ReaGAN: Node-as-Agent-Reasoning | Guo et al. | 2025.08 | 2508.00429 | 智能体图推理 |
| 10 | MemGraphRAG: Memory-based Multi-Agent | Wu et al. | 2026.05 | 2606.00610 | 多智能体记忆 |
| 11 | SAGE: Self-Evolving Graph-Memory Engine | Wang et al. | 2026.05 | 2605.12061 | 自进化记忆 |
| 12 | DOTRAG: Retrieval-Time Reasoning | Moore et al. | 2026.04 | 2605.18760 | 路径推理 |
| 13 | EHRAG: Lightweight GraphRAG via Hypergraph | Song et al. | 2026.04 | 2604.17458 / ACL 2026 | 轻量化 |
| 14 | CrossAug: Cross-Chunk Graph Augmentation | Zhang et al. | 2026.05 | 2605.28004 | 跨块增强 |
| 15 | GraphRAG on Consumer Hardware | Fernandes et al. | 2026.05 | 2605.20815 | 边缘部署 |
| 16 | AtomicRAG: Atom-Entity Graphs | Hou et al. | 2026.02 | 2604.20844 | 知识粒度 |
| 17 | CuraView: Medical Hallucination Detection | Ye et al. | 2026.05 | 2605.03476 | 医疗应用 |
| 18 | LegalGraphRAG: Legal Reasoning | Chen et al. | 2026.05 | 2605.28120 | 法律应用 |
| 19 | Agentic GraphRAG for Financial Data | Capozzi et al. | 2026.04 | 2605.18770 | 金融应用 |
| 20 | Graph-Structured Info for Pest Control | Li et al. | 2025.12 | 2512.21837 | 农业应用 |
| 21 | SEM-RAG: Telecom Standards | Yang et al. | 2026.05 | 2605.08997 | 电信应用 |
| 22 | LLMs+Graphs: Graph-Native AI Systems | Khan et al. | 2026.06 | 2606.11560 / PAKDD 2026 | 综述 |
| 23 | RoGRAD: Robust Graph Learning | Wang et al. | 2025.10 | 2510.01910 | 鲁棒性基准 |
| 24 | GraphInfer-Bench: LLM Graph Inference | Peng et al. | 2026.06 | 2606.11562 | 推理基准 |
| 25 | PersonalAI 2.0: KG Traversal with Planning | Menschikov et al. | 2026.05 | 2605.13481 | 个人AI |
| 26 | XGRAG: Explaining KG-based RAG | Li et al. | 2026.04 | 2604.24623 | 可解释性 |
| 27 | KGiRAG: Iterative GraphRAG for Sensemaking | Iacob et al. | 2026.04 | 2604.20859 | 迭代检索 |
| 28 | Why Neighborhoods Matter in Agentic GraphRAG | Terrenzi et al. | 2026.05 | 2605.15109 | 邻域遍历 |
| 29 | RLM-on-KG: Adaptive Retrieval Control | Volpini et al. | 2026.04 | 2604.17056 | 自适应检索 |
| 30 | GraphRAG-IRL: Personalized Recommendation | Liang et al. | 2026.04 | 2604.19128 | 推荐系统 |

---

## 九、总结与展望

### 9.1 核心结论

2025–2026年，GraphRAG与GNN的结合从"GNN作为外部工具"演进为"图-语言原生融合"。主要表现为：

1. **编码器层**: 从黑盒GNN → 查询条件化GNN → 可解释GNN（M-GNAN）
2. **架构层**: GNN+LLM流水线 → 图结构注入LLM注意力（GTLM, 0.015%参数）
3. **系统层**: 静态检索 → 智能体化自进化记忆（SAGE, ReaGAN）
4. **应用层**: 通用QA → 垂直领域（医疗、法律、金融、农业、电信）

### 9.2 未来方向

- **统一图-语言架构**: GTLM证明了图结构可以直接注入LLM注意力，未来可能出现完全消除GNN/LLM边界的统一模型
- **动态图实时更新**: 当前GraphRAG多为静态索引，如何在流式数据中实时更新图结构是重要挑战
- **多模态GraphRAG**: 结合文本、图像、代码的多模态图检索增强生成
- **端到端可训练流水线**: 当前多数系统为分阶段设计，端到端训练可优化全局目标
- **可解释性与可信度**: Ex-GraphRAG开创的可解释证据路由方向，对高风险应用至关重要

---

> **免责声明**: 本综述基于arXiv预印本和已录用论文整理，部分论文可能尚未经过完整同行评审。论文信息截至2026年6月13日。
