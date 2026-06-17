# 模块E：科学计算参考文档

## 概述

Scientific Agent Skills 提供138项科学技能+100+数据库，覆盖生物信息学、化学信息学、药物发现、物理学、天文学、地理空间、临床研究等领域。基于Agent Skills开放标准，兼容Cursor/Claude Code/Codex。

## 技能分类索引

### 🧬 生物信息学与基因组学

| 技能 | 用途 |
|------|------|
| `scanpy` | 单细胞RNA-seq分析（预处理、降维、聚类、差异表达） |
| `biopython` | 序列I/O、比对、BLAST、系统发育、结构分析 |
| `deeptools` | NGS数据深度分析（覆盖度、热图、峰注释） |
| `geniml` | 基因组区域ML嵌入（Region2Vec、SCEMBED） |
| `anndata` | 注释数据矩阵操作（H5AD读写、合并、切片） |
| `arboreto` | 基因调控网络推断（GRNBoost2等算法） |
| `cellxgene-census` | CZ CELLxGENE单细胞数据查询 |
| `depmap` | 癌症依赖性图谱数据访问 |
| `gget` | 20+基因组数据库统一查询 |
| `bioservices` | ~40个生物信息学Web服务接口 |

### 🧪 化学信息学与药物发现

| 技能 | 用途 |
|------|------|
| `rdkit` | 分子操作、指纹、描述符、子结构搜索 |
| `deepchem` | 分子属性预测、虚拟筛选、ADMET |
| `datamol` | 分子I/O、描述符计算、反应数据 |
| `diffdock` | 分子对接（扩散模型） |
| `cobrapy` | 代谢网络建模与FBA |
| `esm` | 蛋白质语言模型（ESM3/ESM-C/Forge） |

### 🔬 蛋白质组学与结构生物学

| 技能 | 用途 |
|------|------|
| `flowio` | 流式细胞术数据读写 |
| `diffdock` | 蛋白质-配体对接 |
| `esm` | 蛋白质序列设计与结构预测 |

### 🏥 临床研究与精准医学

| 技能 | 用途 |
|------|------|
| `clinical-decision-support` | 临床决策辅助（诊断、治疗方案建议） |
| `clinical-reports` | 临床报告生成（影像、实验室、用药） |
| `benchling-integration` | Benchling LIMS集成 |
| `dnanexus-integration` | DNAnexus云平台集成 |

### 🌍 地理空间与遥感

| 技能 | 用途 |
|------|------|
| `geopandas` | 地理数据框操作（CRS管理、空间连接、I/O） |
| `geomaster` | 高级GIS（卫星图像、遥感、大数据、空间统计） |
| `bids` | 神经影像数据标准（BIDS格式） |

### 🤖 ML/AI与数据科学

| 技能 | 用途 |
|------|------|
| `dask` | 大规模并行计算（DataFrame、Array、Bag） |
| `exploratory-data-analysis` | 自动化EDA（统计摘要、可视化、异常检测） |
| `exa-search` | Exa AI学术搜索 |
| `cirq` | 量子电路构建与模拟 |

### 🔮 物理学与天文学

| 技能 | 用途 |
|------|------|
| `astropy` | 天文坐标变换、宇宙学计算、FITS文件、时间、单位 |
| `fluidsim` | 流体动力学模拟 |

### 📊 科研生产力工具

| 技能 | 用途 |
|------|------|
| `citation-management` | 文献管理（Zotero集成、引用格式化） |
| `docx` | Word文档创建/编辑（评论、修改追踪） |
| `generate-image` | 科研插图生成 |
| `bgpt-paper-search` | 论文搜索 |
| `autoskill` | 自动技能生成（从文档生成SKILL.md） |

## 100+数据库列表

### 化学/药物
`PubChem` · `ChEMBL` · `DrugBank` · `ZINC` · `ChEBI` · `Brenda`

### 蛋白质/结构
`UniProt` · `PDB` · `InterPro` · `STRING` · `EMDB`

### 基因组/变异
`COSMIC` · `ClinVar` · `gnomAD` · `dbSNP` · `Ensembl` · `GTEx` · `ENCODE`

### 基因表达
`GEO` · `SRA` · `ENA` · `HCA` · `TCGA-GDC`

### 通路/网络
`KEGG` · `Reactome` · `BioGRID` · `DisGeNET` · `Monarch`

### 临床/药物安全
`ClinicalTrials.gov` · `DailyMed` · `FDA` · `ClinPGx` · `HPO` · `OMIM`

### 经济金融
`FRED` · `BLS` · `Census` · `Treasury` · `BEA` · `ECB` · `Eurostat`

### 物理/地球科学
`NIST` · `NASA` · `NOAA` · `USGS` · `EPA` · `SDSS` · `SIMBAD`

### 知识产权
`USPTO`

### 其他
`Addgene` · `WHO` · `COD`

## 工作流示例

### 单细胞RNA-seq分析

```python
import scanpy as sc

adata = sc.read("data.h5ad")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
adata = adata[:, adata.var.highly_variable]
sc.tl.pca(adata, svd_solver='arpack')
sc.pp.neighbors(adata, n_neighbors=10, n_pcs=40)
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.rank_genes_groups(adata, 'leiden', method='wilcoxon')
```

### 分子对接 (DiffDock)

```python
# 准备批处理CSV
# protein_path, ligand_smiles
# 5ht2a.pdb, CC(C)NCC(O)COc1cccc2ccccc12

python scripts/prepare_batch_csv.py --protein_dir ./proteins --ligands_file ligands.csv
python scripts/analyze_results.py --results_dir ./output
```

### 蛋白质序列分析 (BioPython)

```python
from Bio import SeqIO
from Bio.Align import PairwiseAligner

for record in SeqIO.parse("sequences.fasta", "fasta"):
    print(f">{record.id} len={len(record.seq)} gc={100*(record.seq.count('G')+record.seq.count('C'))/len(record.seq):.1f}%")

aligner = PairwiseAligner()
aligner.mode = 'global'
alignments = aligner.align(seq1, seq2)
```

### 天文学数据 (AstroPy)

```python
from astropy.coordinates import SkyCoord
from astropy import units as u

coord = SkyCoord(ra=10.68458*u.deg, dec=41.26917*u.deg, frame='icrs')
coord.galactic

from astropy.cosmology import Planck18
Planck18.angular_diameter_distance(z=0.5)
```

### Dask大规模计算

```python
import dask.dataframe as dd

df = dd.read_csv("large_dataset/*.csv")
result = df.groupby('category').amount.mean().compute()
```

## 安装

```bash
git clone https://github.com/K-Dense-AI/scientific-agent-skills
cp -r scientific-agent-skills/scientific-skills/* .trae/skills/
```

## K-Dense BYOK

免费的桌面AI协科学家，使用科学Agent技能。自带API密钥，支持40+模型，100+科学数据库。

```bash
git clone https://github.com/K-Dense-AI/k-dense-byok
```
