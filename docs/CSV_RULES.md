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

## **Quick Reference**
- **Commas in text** → Quote the field
- **Newlines in text** → Quote the field  
- **Quotes in text** → Double them (`""`) and quote the field
- **Empty field** → Leave blank or use `""`
- **Safe characters** → Letters, numbers, spaces, basic punctuation (when not comma/quote/newline)

The error you encountered (`TypeError: '<' not supported between instances of 'NoneType' and 'str'`) occurred because unquoted commas in the prompt and options fields created extra columns, resulting in a `None` key in the dictionary that Flask couldn't serialize to JSON.