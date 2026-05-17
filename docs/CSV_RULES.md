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

## **8. Video URL Formatting**
The `video_url` column is optional and supports YouTube video links for question introductions.

### **Supported YouTube URL Formats:**
```csv
✅ ALL CORRECT:
q_auto_05,2025,MCQ,"Question","Options",C,https://youtu.be/v6fNh1AxZ-M
q_auto_06,2025,MCQ,"Question","Options",C,https://www.youtube.com/watch?v=LDdrLWiJJxc
q_auto_11,2025,MCQ,"Question","Options",B,https://www.youtube.com/embed/GyeQd_iOikY
```

### **Empty Video URL (No Video):**
```csv
✅ CORRECT (no video - shows "Eyes on Teacher"):
q_auto_15,2025,MCQ,"Question","Options",D,
                                         ↑
                                    Empty field
```

### **Video URL Rules:**
- **Use YouTube unlisted videos** (not private, not public)
- **No commas in URL** - YouTube URLs don't contain commas, so no quoting needed
- **Leave empty if no video** - Students will see "Eyes on Teacher 👀" message
- **Same video for related questions** - OK to reuse URLs (e.g., Q26.1, Q26.2, Q26.3 share same video)

### **URL Formats Supported:**
- `https://youtu.be/VIDEO_ID` ← Recommended (shortest)
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

**See [VIDEO.md](VIDEO.md) for complete video integration documentation.**

## **Quick Reference**
- **Commas in text** → Quote the field
- **Newlines in text** → Quote the field  
- **Quotes in text** → Double them (`""`) and quote the field
- **Empty field** → Leave blank or use `""`
- **SHORT questions** → Must include empty `options` field (two commas `,,`)
- **Video URLs** → Use YouTube unlisted links (`https://youtu.be/VIDEO_ID`)
- **No video** → Leave `video_url` field empty
- **Safe characters** → Letters, numbers, spaces, basic punctuation (when not comma/quote/newline)

The error you encountered (`TypeError: '<' not supported between instances of 'NoneType' and 'str'`) occurred because unquoted commas in the prompt and options fields created extra columns, resulting in a `None` key in the dictionary that Flask couldn't serialize to JSON.