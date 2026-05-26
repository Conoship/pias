# PIAS AI Agent Testing Document

## 1

The tests cover:

- Starting the UI.
- Selecting the required input files.
- Entering the required vessel values.
- Parsing main dimensions, layouts, and openings input files.
- Running the model pipeline.
- Displaying the predicted attained index, confidence interval, and pass/fail comparison.
- Handling missing or invalid input.

## 2. Test Data

| Input | Example file/value | Notes |
| --- | --- | --- |
| Main dimensions PDF |  | Required |
| Openings PDF |  | Required (we only use layout and main) |
| Layouts XML |  | Required |
| Subdivision length |  | Numeric |
| Light service draft |  | Numeric |
| Subdivision draft |  | Numeric |
| Light GM value |  | Numeric |
| Partial GM value |  | Numeric |
| Deep GM value |  | Numeric |

## 3. Acceptance Test Cases

### AT-01: Start Application

| Field | Description |
| ----- | ----------- |
| Objective | Test that the desktop UI opens successfully. |
| Steps | Open PowerShell in the project root and run  `python main.py`. |
| Expected result | The main application window opens with file inputs and a run button. |
| Actual result | The main application window opened with the file inputs and a run button. |
| Status | Passed |

### AT-02: Browse Required Files

| Field | Description |
| ----- | ----------- |
| Objective | Test that each browse button fills the correct file field. |
| Steps |  Click the browse button and select a RTF/XML |
| Expected result | Each selected file path appears in the matching input field. |
| Actual result |  |
| Status |  |

### AT-03: Missing File Validation

| Field | Description |
| --- | --- |
| Objective | test that the app prevents running without all required files. |
| Steps |Leave one or more file fields empty and Click Run. |
| Expected result | The app does not run the pipeline and shows a message for the missing file. |
| Actual result |  |
| Status |  |

### AT-04: Missing Value Validation

| Field | Description |
| --- | --- |
| Objective | test that the app prevents running without all required user values. |
| Steps | Leave one numeric value empty and Click Run. |
| Expected result | The app does not run the pipeline and shows a message for the missing value. |
| Actual result |  |
| Status |  |

### AT-05: Invalid Numeric Value

| Field | Description |
| --- | --- |
| Objective | test that text in a numeric field is handled safely. |
| Steps | 1. Enter non-numeric text `abc` in a numeric field and click Run. |
| Expected result | The app rejects the input or shows a clear error. |
| Actual result |  |
| Status |  |

### AT-06: Successful Prediction

| Field | Description |
| --- | --- |
| Objective | test the complete pipepline  from input to prediction. |
| Steps | Select all required files. Fill all required values. Click Run. |
| Expected result | The results area displays the predicted attained index, a 95% confidence interval, and a comparison against required index R. |
| Actual result |  |
| Status |  |

### AT-07: Required Index Comparison - Pass

| Field | Description |
| --- | --- |
| Objective | test the message when predicted A is above or equal to R. |
| Steps | Enter a required index R lower than or equal to the expected prediction.|
| Expected result | The results should correctly display that the ship passes the damage stability calculation|
| Actual result |  |
| Status |  |

### AT-08: Invalid Layouts XML

| Field | Description |
| --- | --- |
| Objective | test behavior when the Layouts XML does not contain the expected table. |
| Steps | Select an XML without the needed layout tables for the layouts input.|
| Expected result | The app handles the missing Layouts data safely and shows a clear error or empty-data result. |
| Actual result |  |
| Status |  |

### AT-09: Invalid main Dimensions RTF

| Field | Description |
| --- | --- |
| Objective | test behavior when the dimension RTF is malformed or not a PIAS layout file. |
| Steps | Select an invalid RTF file for the dimension input without the needed tables. |
| Expected result | The app handles the failure safely and shows a clear error instead of crashing. |
| Actual result |  |
| Status |  |

### AT-10: Missing Model File

| Field | Description |
| --- | --- |
| Objective | test behavior when the model file is unavailable. |
| Steps | Make `models/model.pkl` unavailable. |
| Expected result | The app shows a clear error that the model could not be loaded. |
| Actual result |  |
| Status |  |

### AT-11: Model File Loads Successfully

| Field | Description |
| --- | --- |
| Objective | test that the saved model can be loaded from `models/model.pkl`. |
| Steps | Run the pipeline with valid input files and values. |
| Expected result | The model file loads without file error. |
| Actual result |  |
| Status |  |

### AT-12: Model Uses the Correct Feature Columns

| Field | Description |
| --- | --- |
| Objective | test that the input dataframe contains all features expected by the saved model. |
| Steps | Run the pipeline with valid input files and values. |
| Expected result | The pipeline selects the model feature columns without a missing-column error. |
| Actual result |  |
| Status |  |

### AT-13: Engineered Features Are Applied

| Field | Description |
| --- | --- |
| Objective | test that the engineered features are derived sucessfully . |
| Steps | Run the pipeline using a model file. |
| Expected result | The engineered features are created before prediction. |
| Actual result |  |
| Status |  |

### AT-14: Confidence Interval Is Valid

| Field | Description |
| --- | --- |
| Objective | test that the confidence interval is shown correctly. |
| Steps | Run the full prediction pipeline with valid input. |
| Expected result | the prediction must fall within the bounds of the interval |
| Actual result |  |
| Status |  |

### AT-15: Random Forest

| Field | Description |
| --- | --- |
| Objective | test that a Random Forest model calculates confidence bounds and attained index. |
| Steps | Run the pipeline with a saved Random Forest model. |
| Expected result | The app calculates the prediction and the interval correctly. |
| Actual result |  |
| Status |  |

### AT-16: MAPIE XGB Prediction Path

| Field | Description |
| --- | --- |
| Objective | test that a MAPIE XGB model uses the interval and gives a valid prediction. |
| Steps | Run the pipeline with a saved model. |
| Expected result | The app displays prediction, lower bound, and upper bound. |
| Actual result |  |
| Status |  |

### AT-17: Changed Input Changes Model Output

| Field | Description |
| --- | --- |
| Objective | test that model output corresponds to changed vessel input values. |
| Steps | Run a prediction and change one  numeric value such as subdivision draft or GM value then run again. |
| Expected result | The pipeline completes and the result is recalculated for the changed input. |
| Actual result |  |
| Status |  |

### AT-18: Empty Parsed Data Handling

| Field | Description |
| --- | --- |
| Objective | test behavior when one parser returns no usable rows. |
| Steps | Use a file that contains no usable data for one parser and click Run. |
| Expected result | The app stops safely and displays a message. |
| Actual result |  |
| Status |  |

### AT-19: Model Result Formatting

| Field | Description |
| --- | --- |
| Objective | test that model results are readable in the UI. |
| Steps | Run a successful prediction. |
| Expected result | The prediction is rounded and the confidence interval is displayed as `[lower, upper]`. |
| Actual result |  |
| Status |  |

### AT-20: Extreme Numeric Values

| Field | Description |
| --- | --- |
| Objective | test that the model pipeline handles unusually high inputs safely. |
| Steps | Enter  numeric values for draft, GM, or subdivision length and click Run. |
| Expected result | The app either produces a result or shows a clear validation error without crashing. |
| Actual result |  |
| Status |  |

## 6. Defects Found

| ID  | Test case | Description | Status |
| --- | --------- | ----------- | ------ |
|     |           |             |        |

## 7. Summary

| Result | Count |
| ---    | ---   |
| Passed |       |
| Failed |       |
