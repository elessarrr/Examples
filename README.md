Thanks for taking the time to review my submission.

## Personal particulars
Full name : Bhavesh Rajwani
email address: rajwani.b@outlook.com

## Overview of the submitted folder and the folder structure:

## Instructions:

## Description of logical steps/flow of the pipeline: 

Overview of key findings from EDA conducated in Task 1 and the choices made in the pipeline based on these findings, particularly any feature engineering. Please keep the details of the EDA in the `.ipynb`, this section should be a quick
summary:

- As part of preprocessing, I ingested the data into a dataframe, and pulled snapshots and descriptions of the distribution to see what I was dealing with.
- I then checked for duplicates, empty cells, categorical and numerical variables, and non-standard data (e.g. two different words to represent the same result). I 'solved' errors where they were spotted.
- I thenn created a correlation heatmap and a consequential pairplot of highest correlation pairs(limited by number of graphs I can fit comfortably on a page) to eyeball the data and see if I was missing any causality.
- I then converted the categorical variables to numerical form to allow machine learning models to understand them.
- Next, I split the data into training and test sets. I then imported modules of my three chosen machine learning models, fit them to the test data, predicted results, and scored them against actual results.
- For each model, I ran hyper parameter tuning and checked those results as well. 
- Best scores for each model were extracted and stored in the final output csv file 'model_score.csv'

## Explanation of your choice of models for each machine learning task.

- Given this is a classification task, I wanted to pick a model usually used for classification since we are trying to get to a 'survive' or 'not survive' answer. Typically we choose from Random Forest, Naive Bayes, Kernel SVM, Linear SVM Gradient Boosting Tree, among others, for such tasks. I referred to this post to narrow down my choices and picked models that I was more familiar with:
https://blogs.sas.com/content/subconsciousmusings/files/2017/04/machine-learning-cheet-sheet-2.png
- For each model, I picked hyperparameter tuning and scoring per what I've studied and read from online courses and other resources (Datacamp, Medium etc.)

## Evaluation of the models developed. Any metrics used in the evaluation should also be explained.
- As you can see, I worked to predict results in all models based on the training set that had been split and used for all models. I then scored each prediction against the y_train set, which represents the true result.
- Simply put, higher score = more accurate model.
- Random Forest score is too high; from experience, I realise I've probably missed a step somewhere. If I had more time, I would consult a senior or more experienced colleague to see what I may have missed.


## Other considerations for deploying the models developed.

- Suggest running such models in Colab or Docker where possible, which have environments set up. Personally I can't use XGBoost on my laptop due to compatibility issues, and wonder if with all the dependencies in the models, if someone else might have trouble running them too.

