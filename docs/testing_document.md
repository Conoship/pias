# AI Agent to predict damage stability Testing Document

## 1. Overview

The Tests cover:

- Starting the UI.
- Selecting the required input files.
- Entering the required vessel values.
- Parsing main dimensions, layouts, and openings input files.
- Running the model pipeline.
- Displaying the predicted attained index, confidence interval, and pass/fail comparison.
- Handling missing or invalid input.

## 2. Test Data

| Input | Example file/value | Notes |
| ----- | ----------- | --- |
| Main dimensions PDF | | Required |
| Layouts XML | | Required |
| Subdivision length | | Numeric |
| Light service draft | | Numeric |
| Subdivision draft | | Numeric |
| Light GM value | | Numeric |
| Partial GM value | | Numeric |
| Deep GM value | | Numeric |

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
| Steps | Click the browse buttons and select a RTF/XML |
| Expected result | Each selected file path appears in the matching input field. |
| Actual result | Each selected file path appeared in the matching input field. |
| Status | Passed |

### AT-03: Missing File Validation

| Field | Description |
| ----- | ----------- |
| Objective | Test that the app prevents running without all required files. |
| Steps | Leave one or more file fields empty and click Run. |
| Expected result | The app does not run the pipeline and shows a message for the missing file. |
| Actual result | The app did not run the pipeline and showed a message for the missing file. |
| Status | Passed |

### AT-04: Missing Value Validation

| Field | Description |
| ----- | ----------- |
| Objective | Test that the app warns about running without all required user values. |
| Steps | Leave one or more numeric values empty and click Run. |
| Expected result | The app shows a warning message about running with empty values. |
| Actual result | The app showed a warning message about running with empty values. |
| Status | Passed |

### AT-05a: Invalid Numeric Value - Non Numeric input

| Field | Description |
| ----- | ----------- |
| Objective | Test that text in a numeric field is handled safely. |
| Steps | Enter non-numeric text `abc` in a numeric field and click Run. |
| Expected result | The app informs the user about the invalid input and does not run the pipeline. |
| Actual result | The app informed the user about the invalid input and did not run the pipeline. |
| Status | Passed |

### AT-05b: Invalid Numeric Value - Negative input

| Field | Description |
| ----- | ----------- |
| Objective | Test that text in a numeric field is handled safely. |
| Steps | Enter a negative value in a numeric field and click Run. |
| Expected result | The app informs the user about the invalid input and does not run the pipeline. |
| Actual result | The app informed the user about the invalid input and did not run the pipeline. |
| Status | Passed |

### AT-06: Successful Prediction

| Field | Description |
| ----- | ----------- |
| Objective | Test the complete pipepline from input to prediction. |
| Steps | Select all required files. Fill all required values. Click Run. |
| Expected result | The results area displays the predicted attained indices, a 95% confidence interval, and a comparison against each required index R. |
| Actual result | The results area displayed the predicted attained indices, a 95% confidence interval, and a comparison against each required index R. |
| Status | Passed |

### AT-07: Required Index Comparison - Pass

| Field | Description |
| ----- | ----------- |
| Objective | Test the message when predicted A is above or equal to R. |
| Steps | Enter a required index R lower than or equal to the expected prediction. |
| Expected result | The results should correctly display that the ship passes the damage stability calculation. |
| Actual result | |
| Status | |

### AT-08a: Invalid Main Dimensions RTF

| Field | Description |
| ----- | ----------- |
| Objective | Test behavior when the Main Dimensions RTF is malformed. |
| Steps | Select an invalid RTF file for the Main Dimensions input without one or more of the required tables. |
| Expected result | The app handles the missing Main Dimensions data safely and shows a clear error displayign the missing columns. |
| Actual result | The app handled the missing Main Dimensions data safely and showed a clear error displaying the missing columns. |
| Status | Passed |

### AT-08b: Valid Main Dimensions RTF

| Field | Description |
| ----- | ----------- |
| Objective | Test behavior when the Main Dimensions RTF is not malformed. |
| Steps | Select a valid RTF file for the Main Dimensions with all of the required tables. |
| Expected result | The app moves on to Layouts parsing. |
| Actual result | The app moved on to Layouts parsing. |
| Status | Passed |

### AT-09a: Invalid Layouts XML

| Field | Description |
| ----- | ----------- |
| Objective | Test behavior when the Layouts XML does not contain the required table. |
| Steps | Select an invalid XML file for the Layouts input without one or more of the required tables. |
| Expected result | The app handles the missing Layouts data safely and shows a clear error displaying the missing columns. |
| Actual result | The app handled the missing Layouts data safely and showed a clear error displaying the missing columns. |
| Status | Passed |

### AT-09b: Valid Layouts XML

| Field | Description |
| ----- | ----------- |
| Objective | Test behavior when the Layouts XML contains the expected table. |
| Steps | Select a valid XML with all of the required tables. |
| Expected result | The app moves on to user defined values validation. |
| Actual result | The app moved on to the user defined values validation |
| Status | Passed |

### AT-10: Missing Model File

| Field | Description |
| ----- | ----------- |
| Objective | Test behavior when the model file is unavailable. |
| Steps | Make `models/model.pkl` unavailable. |
| Expected result | The app shows a clear error that the model could not be loaded and does not display any results. |
| Actual result | The app showed a clear error that the model could not be loaded and did not display any results. |
| Status | Passed |

### AT-11: Model File Loads Successfully

| Field | Description |
| ----- | ----------- |
| Objective | Test that the saved model can be loaded from `models/model.pkl`. |
| Steps | Run the pipeline with valid input files and values. |
| Expected result | The model file loads without file error. |
| Actual result | The model file loaded without file error. |
| Status | Passed |

### AT-12: Model Uses the Correct Feature Columns

| Field | Description |
| ----- | ----------- |
| Objective | Test that the input dataframe contains all features expected by the saved model. |
| Steps | Run the pipeline with valid input files and values. |
| Expected result | The pipeline selects the model feature columns without a missing-column error. |
| Actual result | |
| Status | |

### AT-13: Engineered Features Are Applied

| Field | Description |
| ----- | ----------- |
| Objective | Test that the engineered features are derived sucessfully . |
| Steps | Run the pipeline using a model file. |
| Expected result | The engineered features are created before prediction. |
| Actual result | |
| Status | |

### AT-14: Confidence Interval Is Valid

| Field | Description |
| ----- | ----------- |
| Objective | Test that the confidence interval is shown correctly. |
| Steps | Run the full prediction pipeline with valid input. |
| Expected result | The prediction must fall within the bounds of the interval. |
| Actual result | The prediction fell within the bounds of the interval. |
| Status | Passed |

### AT-15: Random Forest

| Field | Description |
| ----- | ----------- |
| Objective | Test that a Random Forest model calculates all attained indexes and the 95% CI bounds. |
| Steps | Run the pipeline with a saved Random Forest model. |
| Expected result | The app displays predictions, lower bound, upper bound and a pass result. |
| Actual result | The app displayed predictions, lower bound, upper bound and a pass result. |
| Status | Passed |

### AT-16: MAPIE XGB Prediction Path

| Field | Description |
| ----- | ----------- |
| Objective | Test that a MAPIE XGB model uses the interval and gives a valid predictions. |
| Steps | Run the pipeline with a saved model. |
| Expected result | The app displays predictions, lower bound, upper bound and a pass result. |
| Actual result | The app displayed predictions, lower bound, upper bound and a pass result. |
| Status | Passed |

### AT-17: Changed Input Changes Model Output

| Field | Description |
| ----- | ----------- |
| Objective | Test that model output corresponds to changed vessel input values. |
| Steps | Run a prediction and change one numeric value and run again. |
| Expected result | The pipeline completes and the result is recalculated for the changed input. |
| Actual result | The pipeline completes and the result is recalculated for the changed input. |
| Status | Passed |

### AT-18: Model Result Formatting

| Field | Description |
| ----- | ----------- |
| Objective | Test that model results are readable in the UI. |
| Steps | Run a successful prediction. |
| Expected result | The prediction is rounded, the confidence intervals are displayed as `[lower, upper]` and the pass results and overall summary are clearly readable. |
| Actual result | The prediction was rounded, the confidence intervals were displayed as `[lower, upper]` and the pass results and overall summary were clearly readable |
| Status | Passed |

### AT-19: Extreme Numeric Values

| Field | Description |
| ----- | ----------- |
| Objective | Test that the model pipeline handles unusually high inputs safely. |
| Steps | Enter  numeric values for draft, GM, or subdivision length and click Run. |
| Expected result | The app either produces a result or shows a clear validation error without crashing. |
| Actual result | |
| Status | |

### AT-20: RTF and XML files are for the same ship

| Field | Description |
| ----- | ----------- |
| Objective | Test that the app checks if the two files are for the same ship. |
| Steps | Enter a XML and a RTF file from two different ship designs and click Run. |
| Expected result | The app warns the user that there is a mismatch between the ships described by the files and does not run the pipeline. |
| Actual result | The app warned the user that there is a mismatch between the ships described by the files and did not run the pipeline. |
| Status | Passed |

## 6. Defects Found

| ID  | Test case | Description | Status |
| --- | --------- | ----------- | ------ |
|     |           |             |        |

## 7. Summary

| Result | Count |
| ------ | ----- |
| Passed |  19   |
| Failed |       |
