# PIAS AI Agent Testing Document

## 1.

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
| Ship name |  | Required |
| Subdivision length |  | Numeric |
| Light service draft |  | Numeric |
| Subdivision draft |  | Numeric |
| Light GM value |  | Numeric |
| Partial GM value |  | Numeric |
| Deep GM value |  | Numeric |
| Required index R |  | Numeric comparison value |

## 3. Acceptance Test Cases

### AT-01: Start Application

| Field | Description |
| --- | --- |
| Objective | Verify that the desktop UI opens successfully. 
| Steps | Open PowerShell in the project root. 
| Expected result | The main application window opens with file inputs and a run button. 
| Actual result 
| Status 

### AT-02: Browse Required Files

| Field | Description |
| --- | --- |
| Objective | Verify that each browse button fills the correct file field. |
| Steps |  Click the browse button and select a rtf/xml |
| Expected result | Each selected file path appears in the matching input field. |
| Actual result |  |
| Status |  |

### AT-03: Missing File Validation

| Field | Description |
| --- | --- |
| Objective | Verify that the app prevents running without all required files. |
| Steps |Leave one or more file fields empty and Click Run. |
| Expected result | The app does not run the pipeline and shows a message for the missing file. |
| Actual result |  |
| Status |  |

### AT-04: Missing Value Validation

| Field | Description |
| --- | --- |
| Objective | Verify that the app prevents running without all required user values. |
| Steps | Leave one numeric value empty and Click Run. |
| Expected result | The app does not run the pipeline and shows a message for the missing value. |
| Actual result |  |
| Status |  |

### AT-05: Invalid Numeric Value

| Field | Description |
| --- | --- |
| Objective | Verify that text in a numeric field is handled safely. |
| Steps | 1. Enter non-numeric text `abc` in a numeric field and click Run. |
| Expected result | The app rejects the input or shows a clear error. |
| Actual result |  |
| Status |  |

### AT-06: Successful Prediction

| Field | Description |
| --- | --- |
| Objective | Verify the complete pipepline  from input to prediction. |
| Steps | Select all required files. Fill all required values. Click Run. |
| Expected result | The results area displays the predicted attained index, a 95% confidence interval, and a comparison against required index R. |
| Actual result |  |
| Status |  |

### AT-07: Required Index Comparison - Pass

| Field | Description |
| --- | --- |
| Objective | Verify the message when predicted A is above or equal to R. |
| Steps | Enter a required index R lower than or equal to the expected prediction.|
| Expected result | The results should correctly display that the ship passes the damage stability calculation|
| Actual result |  |
| Status |  |

### AT-10: Invalid Layouts XML

| Field | Description |
| --- | --- |
| Objective | Verify behavior when the Layouts XML does not contain the expected table. |
| Steps | Select an XML without the needed layout tables for the layouts input.|
| Expected result | The app handles the missing Layouts data safely and shows a clear error or empty-data result. |
| Actual result |  |
| Status |  |

### AT-11: Invalid main Dimensions RTF

| Field | Description |
| --- | --- |
| Objective | Verify behavior when the dimension RTF is malformed or not a PIAS layout file. |
| Steps | Select an invalid RTF file for the dimension input without the needed tables. |
| Expected result | The app handles the failure safely and shows a clear error instead of crashing. |
| Actual result |  |
| Status |  |

### AT-12: Missing Model File

| Field | Description |
| --- | --- |
| Objective | Verify behavior when the model file is unavailable. |
| Steps | Make `models/model.pkl` unavailable. |
| Expected result | The app shows a clear error that the model could not be loaded. |
| Actual result |  |
| Status |  |

## 6. Defects Found

| ID | Test case | Description | Status |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 7. Summary

| Result | Count |
| --- | --- |
| Passed |  |
| Failed |  |



