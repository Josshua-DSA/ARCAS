---
language:
- en
license: cc-by-nc-nd-4.0
size_categories:
- 10K<n<100K
task_categories:
- text-classification
dataset_info:
  features:
  - name: Dates
    dtype: string
  - name: URL
    dtype: string
  - name: News
    dtype: string
  - name: Price Direction Up
    dtype: int64
  - name: Price Direction Constant
    dtype: int64
  - name: Price Direction Down
    dtype: int64
  - name: Asset Comparision
    dtype: int64
  - name: Past Information
    dtype: int64
  - name: Future Information
    dtype: int64
  - name: Price Sentiment
    dtype: string
  splits:
  - name: train
    num_bytes: 1947294
    num_examples: 8456
  - name: test
    num_bytes: 488198
    num_examples: 2114
  download_size: 923564
  dataset_size: 2435492
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
  - split: test
    path: data/test-*
tags:
- finance
- news
- NLP
- Multiclass Classification
- Binary Classification
---
# Dataset Card for Sentiment Analysis of Commodity News (Gold)
This is a news dataset for the commodity market which has been manually annotated for 10,000+ news headlines across multiple dimensions into various classes. The dataset has been sampled from a period of 20+ years (2000-2021).
The dataset was curated by Ankur Sinha and Tanmay Khandait and is detailed in their paper "Impact of News on the Commodity Market: Dataset and Results." It is currently published by the authors on Kaggle, under the Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0) license.

## Dataset Descriptions
- **Homepage:** [Kaggle](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-in-commodity-market-gold) 
- **Repository:**
- **Paper:** [Arxiv](https://arxiv.org/abs/2009.04202) [ResearchGate](https://www.researchgate.net/publication/350914989_Impact_of_News_on_the_Commodity_Market_Dataset_and_Results)

The Kaggle dataset consists of a 1.95MB CSV file, with 10 columns, and 10570 rows.

## Uses
Sentiment Classification

## Dataset Structure

<!-- This section provides a description of the dataset fields, and additional information about the dataset structure such as criteria used to create the splits, relationships between data points, etc. -->
### Data Instances
```
{
  'Dates': '28-01-2016',
  'URL': 'http://www.marketwatch.com/story/april-gold-down-20-cents-to-settle-at-111610oz-2016-01-28',
  'News': 'april gold down 20 cents to settle at $1,116.10/oz',
  'Price Direction Up': 0, 'Price Direction Constant': 0,
  'Price Direction Down': 1,
  'Asset Comparision': 0,
  'Past Information': 1,
  'Future Information': 0,
  'Price Sentiment': 'negative'
}
```

### Data Fields
- Dates: Date of news headline
- URL: URL of news headline
- News: News headline
- Price Direction Up: Does the news headline imply price direction up?
- Price Direction Constant: Does the news headline imply price direction sideways (no change)?
- Price Direction Down: Does the news headline imply price direction down?
- Asset Comparision: Are assets being compared?
- Past Information: Is the news headline talking about past?
- Future Information: Is the news headline talking about future?
- Price Sentiment: Price sentiment of Gold commodity based on headline

### Data Splits
There is currently an train/test split of 80%/20%, with train split having 8456 elements and the test split having 2114 elements. 
Each of the dataset article entries contain a subset of the following features: "Price Direction Up", "Price Direction Constant", "Price Direction Down", "Asset Comparison", "Past Information", "Future Information", "Price Sentiment".
Below is the table for each task, with separate columns for train and test splits:
| Task                     | train                                                                                             | test                                                                                              |
|--------------------------|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **Price Direction Up**   | 0: 4925 (58%)<br>1: 3531 (42%)                                                                   | 0: 1233 (58%)<br>1: 881 (42%)                                                                     |
| **Price Direction Constant** | 0: 8101 (96%)<br>1: 355 (4%)                                                                 | 0: 2025 (96%)<br>1: 89 (4%)                                                                   |
| **Price Direction Down** | 0: 5327 (63%)<br>1: 3129 (37%)                                                                   | 0: 1331 (63%)<br>1: 783 (37%)                                                                     |
| **Asset Comparison**     | 0: 6855 (81%)<br>1: 1601 (19%)                                                                   | 0: 1714 (81%)<br>1: 400 (19%)                                                                     |
| **Past Information**     | 0: 249 (3%)<br>1: 8207 (97%)                                                                    | 0: 69 (3%)<br>1: 2045 (97%)                                                                      |
| **Future Information**   | 0: 8206 (97%)<br>1: 250 (3%)                                                                      | 0: 2045 (97%)<br>1: 69 (3%)                                                                        |
| **Price Sentiment**      | positive: 3531 (42%)<br>negative: 3050 (36%)<br>none: 1574 (19%)<br>neutral: 301 (4%)             | positive: 881 (42%)<br>negative: 764 (36%)<br>none: 394 (19%)<br>neutral: 75 (4%)                 |

## Dataset Creation

### Curation Rationale

<!-- Motivation for the creation of this dataset. -->
Commodity prices are known to be quite volatile. Machine learning models that understand the commodity news well, will be able to provide an additional input to the short-term and long-term price forecasting models. The dataset will also be useful in creating news-based indicators for commodities.

Apart from researchers and practitioners working in the area of news analytics for commodities, the dataset will also be useful for researchers looking to evaluate their models on classification problems in the context of text-analytics. Some of the classes in the dataset are highly imbalanced and may pose challenges to the machine learning algorithms.

[Source](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-in-commodity-market-gold/data)

### Source Data

<!-- This section describes the source data (e.g. news text and headlines, social media posts, translated sentences, ...). -->
The source data is news text and headlines.

Sinha, Ankur, and Tanmay Khandait. "Impact of News on the Commodity Market: Dataset and Results." In Future of Information and Communication Conference, pp. 589-601. Springer, Cham, 2021.

[Source](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-in-commodity-market-gold/data)


#### Data Collection and Processing
The dataset has been collected from various news sources and annotated by three human annotators who were subject experts. Each news headline was evaluated on various dimensions, for instance - if a headline is a price related news then what is the direction of price movements it is talking about; whether the news headline is talking about the past or future; whether the news item is talking about asset comparison; etc.

[Source](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-in-commodity-market-gold/data)
<!-- If the dataset contains annotations which are not part of the initial data collection, use this section to describe them. -->

<!-- #### Annotation process

<!-- This section describes the annotation process such as annotation tools used in the process, the amount of data annotated, annotation guidelines provided to the annotators, interannotator statistics, annotation validation, etc. -->
<!-- 
[More Information Needed]

#### Who are the annotators? -->

<!-- This section describes the people or systems who created the annotations. -->
<!-- 
[More Information Needed]

#### Personal and Sensitive Information

<!-- State whether the dataset contains data that might be considered personal, sensitive, or private (e.g., data that reveals addresses, uniquely identifiable names or aliases, racial or ethnic origins, sexual orientations, religious beliefs, political opinions, financial or health data, etc.). If efforts were made to anonymize the data, describe the anonymization process. -->

<!-- [More Information Needed]

## Bias, Risks, and Limitations

<!-- This section is meant to convey both technical and sociotechnical limitations. -->

<!-- [More Information Needed] -->

<!-- ### Recommendations -->

<!-- This section is meant to convey recommendations with respect to the bias, risk, and technical limitations. -->

<!-- Users should be made aware of the risks, biases and limitations of the dataset. More information needed for further recommendations. --> 

## Kaggle Datatset Description [Source](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-in-commodity-market-gold/data)
### Context
This is a news dataset for the commodity market where we have manually annotated 10,000+ news headlines across multiple dimensions into various classes. The dataset has been sampled from a period of 20+ years (2000-2021).

### Content
The dataset has been collected from various news sources and annotated by three human annotators who were subject experts. Each news headline was evaluated on various dimensions, for instance - if a headline is a price related news then what is the direction of price movements it is talking about; whether the news headline is talking about the past or future; whether the news item is talking about asset comparison; etc.

### Acknowledgements
Sinha, Ankur, and Tanmay Khandait. "Impact of News on the Commodity Market: Dataset and Results." In Future of Information and Communication Conference, pp. 589-601. Springer, Cham, 2021.

https://arxiv.org/abs/2009.04202

Sinha, Ankur, and Tanmay Khandait. "Impact of News on the Commodity Market: Dataset and Results." arXiv preprint arXiv:2009.04202 (2020)

We would like to acknowledge the financial support provided by the India Gold Policy Centre (IGPC).

### Inspiration
Commodity prices are known to be quite volatile. Machine learning models that understand the commodity news well, will be able to provide an additional input to the short-term and long-term price forecasting models. The dataset will also be useful in creating news-based indicators for commodities.

Apart from researchers and practitioners working in the area of news analytics for commodities, the dataset will also be useful for researchers looking to evaluate their models on classification problems in the context of text-analytics. Some of the classes in the dataset are highly imbalanced and may pose challenges to the machine learning algorithms.

## Citation
```
@misc{sinha2020impactnewscommoditymarket,
      title={Impact of News on the Commodity Market: Dataset and Results}, 
      author={Ankur Sinha and Tanmay Khandait},
      year={2020},
      eprint={2009.04202},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2009.04202}, 
}
```

## Dataset Card Authors
Saguaro Capital Management, LLC

## Dataset Card Contact
Tyler Thomas: [tyler@saguarocm.com](mailto:tyler@saguarocm.com)