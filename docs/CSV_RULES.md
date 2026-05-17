# CSV Formatting Rules to Avoid Parsing Errors

Based on the error we encountered, here are the critical rules for creating CSV files that work properly with Python's `csv.DictReader`:

## **1. Quote Fields Containing Commas**
Any field that contains commas MUST be enclosed in double quotes.

```csv
❌ WRONG:
q_auto_05,2025,MCQ,What is the most effective approach to ensuring that automation benefits society as a whole?,A: Option 1, with details|B: Option 2,C

✅ CORRECT:
q_auto_05,2025,MCQ,"What is the most effective approach to ensuring that automation benefits society as a whole?","A: Option 1, with details|B: Option 2",C
```

## **2. Quote Fields Containing Newlines**
Multi-line text fields must be quoted.

```csv
✅ CORRECT:
q_auto_15,2025,SHORT,"Match each scenario:
1. First item
2. Second item
3. Third item",,Answer
```

## **3. Quote Fields Containing Quotes**
If a field contains double quotes, escape them by doubling them and quote the entire field.

```csv
✅ CORRECT:
q_001,2025,MCQ,"He said ""Hello"" to me","A: Yes|B: No",A
```

## **4. Empty Fields**
Empty fields should have no content between commas, or use empty quotes.

```csv
✅ CORRECT:
q_auto_15,2025,SHORT,"Question text",,Answer
```

## **5. Consistent Column Count**
Every row must have the same number of fields as the header.

```csv
✅ CORRECT:
question_id,room_id,type,prompt,options,correct_answer
q_001,2025,MCQ,"Question","Options",Answer
```

## **6. No Trailing Commas**
Don't add extra commas at the end of rows.

```csv
❌ WRONG:
q_001,2025,MCQ,"Question","Options",Answer,

✅ CORRECT:
q_001,2025,MCQ,"Question","Options",Answer
```

## **7. SHORT Question Structure (with video_url)**
SHORT questions must maintain the same 7-column structure as MCQ questions by including an **empty `options` field**.

```csv
✅ CORRECT (7 columns):
question_id,room_id,type,prompt,options,correct_answer,video_url
q_cap_01,2025,SHORT,"Question 29: How do you choose...",,"Answer text",https://youtu.be/5H5ygPCiWKw
                                                         ↑↑
                                                   Empty options field
```

```csv
❌ WRONG (6 columns - missing empty options field):
q_cap_01,2025,SHORT,"Question 29: How do you choose...","Answer text",https://youtu.be/5H5ygPCiWKw
```

**Why this matters:** The CSV parser expects 7 columns. If SHORT questions skip the `options` column, the `correct_answer` gets mapped to `options`, and `video_url` gets mapped to `correct_answer`, breaking video playback and answer validation.

**Structure comparison:**
- **MCQ:** `question_id,room_id,type,prompt,options,correct_answer,video_url`
- **SHORT:** `question_id,room_id,type,prompt,,correct_answer,video_url` ← Note the empty field

## **Quick Reference**
- **Commas in text** → Quote the field
- **Newlines in text** → Quote the field  
- **Quotes in text** → Double them (`""`) and quote the field
- **Empty field** → Leave blank or use `""`
- **SHORT questions** → Must include empty `options` field (two commas `,,`)
- **Safe characters** → Letters, numbers, spaces, basic punctuation (when not comma/quote/newline)

The error you encountered (`TypeError: '<' not supported between instances of 'NoneType' and 'str'`) occurred because unquoted commas in the prompt and options fields created extra columns, resulting in a `None` key in the dictionary that Flask couldn't serialize to JSON.