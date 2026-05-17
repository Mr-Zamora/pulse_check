# Video Integration Guide

## Overview

Pulse Check supports **optional video introductions** for questions. When a teacher clicks "Prepare Question," students can watch a YouTube video before the quiz starts. This provides context, engagement, and multimodal learning.

---

## How It Works

### **Workflow**

1. **Teacher clicks "Prepare Question"**
   - If `video_url` exists → Students see YouTube video auto-playing
   - If `video_url` is empty → Students see "Eyes on Teacher 👀" message

2. **WAITING State (Instruction Time)**
   - Video plays (or teacher presents verbally)
   - Timer counts down
   - Students cannot submit yet

3. **Teacher clicks "Start Quiz Now"**
   - Video stops/hides
   - Question form appears
   - Students can now submit answers

---

## Adding Videos to Questions

### **Step 1: Upload to YouTube**

1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click **"Create"** → **"Upload videos"**
3. Upload your 1-minute introduction video
4. Set visibility to **"Unlisted"** (not public, but accessible via link)
5. Copy the video URL (e.g., `https://youtu.be/abc123def`)

### **Step 2: Add URL to CSV**

Edit `database/questions.csv` and add the `video_url` column:

```csv
question_id,room_id,type,prompt,options,correct_answer,video_url
q_auto_05,2025,MCQ,"Question 5: What is...","A: Option A|B: Option B",C,https://youtu.be/abc123
q_auto_06,2025,MCQ,"Question 6: A real estate...","A: Linear|B: Polynomial",C,https://youtu.be/def456
q_auto_15,2025,MCQ,"Question 15: Which type...","A: Supervised|B: Unsupervised",D,
```

**Important:**
- Leave `video_url` **empty** if no video (defaults to "Eyes on Teacher")
- Use **YouTube** or **Vimeo** URLs only
- Videos should be **unlisted** (not private, not public)

---

## CSV Rules for Video URLs

Follow the same [CSV formatting rules](CSV_RULES.md):

### ✅ **Correct Examples**

```csv
q_001,2025,MCQ,"Question text","Options",A,https://youtu.be/abc123
q_002,2025,MCQ,"Question text","Options",B,
q_003,2025,SHORT,"Question text",,Answer,https://www.youtube.com/watch?v=xyz789
```

### ❌ **Incorrect Examples**

```csv
# Missing column (must have 7 columns if video_url exists in header)
q_001,2025,MCQ,"Question text","Options",A

# URL contains comma without quotes (will break parsing)
q_002,2025,MCQ,"Question","Options",B,https://example.com?v=123,param=value
```

**Rule:** If your URL contains commas, quote the entire field:
```csv
q_002,2025,MCQ,"Question","Options",B,"https://example.com?v=123,param=value"
```

---

## Student Experience

### **With Video (WAITING State)**

```
┌─────────────────────────────────────┐
│  🎥 Introduction Video              │
│                                     │
│  [YouTube Video Player]             │
│  ▶ Playing...                       │
│                                     │
│  Question will appear when the      │
│  teacher starts the quiz            │
│                                     │
│  Timer: 01:45                       │
└─────────────────────────────────────┘
```

### **Without Video (WAITING State)**

```
┌─────────────────────────────────────┐
│  State: WAITING                     │
│                                     │
│  👀 Eyes on Teacher                 │
│                                     │
│  Listen to the instructions.        │
│  The question will appear when      │
│  the quiz starts.                   │
│                                     │
│  Timer: 01:45                       │
└─────────────────────────────────────┘
```

### **Quiz Active (Both Cases)**

```
┌─────────────────────────────────────┐
│  Question 5: What is the best way...│
│                                     │
│  ○ A: Let businesses handle it      │
│  ○ B: Focus only on tech speed      │
│  ○ C: Have governments work together│
│  ○ D: Stop using automation         │
│                                     │
│  [Submit Answer]                    │
│                                     │
│  Timer: 01:58                       │
└─────────────────────────────────────┘
```

---

## Teacher Experience

### **Control Panel**

The teacher sees the same controls regardless of video presence:

1. **Select Question** → Dropdown shows all questions
2. **Set Instruction Time** → How long students watch/listen (default: 2 min)
3. **Set Quiz Time** → How long students have to answer (default: 2 min)
4. **Click "Prepare Question"** → Video starts (or "Eyes on Teacher" appears)
5. **Click "Start Quiz Now"** → Question form appears for students

---

## Pedagogical Benefits

### **With Video**
- ✅ **Multimodal learning** - Visual + auditory input
- ✅ **Contextual scaffolding** - Background before question
- ✅ **Engagement** - Movement captures attention
- ✅ **Accessibility** - Supports ESL/ELL students
- ✅ **Shared experience** - Whole class watches together

### **Without Video**
- ✅ **Teacher-led instruction** - Direct verbal explanation
- ✅ **Flexibility** - Adapt to classroom needs
- ✅ **Interactive** - Q&A during instruction time
- ✅ **Low bandwidth** - Works in any environment

---

## Technical Details

### **Supported Platforms**
- ✅ YouTube (recommended)
- ✅ Vimeo
- ✅ Any embeddable video URL

### **Video Requirements**
- **Duration:** 1-3 minutes recommended
- **Visibility:** Unlisted (not private)
- **Format:** Any format YouTube/Vimeo supports
- **Captions:** Recommended for accessibility

### **Bandwidth Considerations**
- Videos stream from YouTube/Vimeo (not your server)
- No storage costs
- Adaptive quality (auto-adjusts to student internet speed)
- Works on mobile devices

---

## Troubleshooting

### **Video doesn't play**
- Check URL is correct and video is **unlisted** (not private)
- Ensure video is not age-restricted or region-blocked
- Test URL in incognito browser window

### **Video shows but doesn't auto-play**
- Some browsers block auto-play with sound
- Students may need to click play button once
- Use muted auto-play as fallback

### **Students joined late and missed video**
- Video continues playing during WAITING state
- Late joiners see video from current timestamp
- Teacher can restart question if needed

---

## Best Practices

1. **Keep videos short** (1-2 minutes ideal)
2. **Use unlisted visibility** (not public, not private)
3. **Add captions** for accessibility
4. **Test videos** before class
5. **Have backup plan** if video fails (verbal explanation)
6. **Set instruction time** slightly longer than video duration

---

## Example Question with Video

```csv
question_id,room_id,type,prompt,options,correct_answer,video_url
q_auto_05,2025,MCQ,"Question 5: What is the best way to make sure that automation and robots help society instead of causing harm?","A: Let businesses handle it completely and hope the economy grows naturally.|B: Focus only on tech speed and profits, and fix social problems later.|C: Have governments, schools, and businesses work together to help workers learn new skills.|D: Stop using automation in fields where a lot of people work.",C,https://youtu.be/dQw4w9WgXcQ
```

**Result:**
- Teacher clicks "Prepare Question"
- Students see 1-minute YouTube video about automation and society
- Instruction timer counts down (e.g., 2:00 → 1:00)
- Teacher clicks "Start Quiz Now"
- Video stops, question appears with 4 options
- Students submit answers during quiz time

---

## Migration Guide

### **Existing Questions (No Videos)**

Your existing `questions.csv` will continue to work! Simply add an empty `video_url` column:

**Before:**
```csv
question_id,room_id,type,prompt,options,correct_answer
q_001,2025,MCQ,"Question","Options",A
```

**After:**
```csv
question_id,room_id,type,prompt,options,correct_answer,video_url
q_001,2025,MCQ,"Question","Options",A,
```

All questions without video URLs will show "Eyes on Teacher 👀" as before.

---

## Future Enhancements

Potential features to consider:

- [ ] Video replay button for late joiners
- [ ] Progress bar showing video completion
- [ ] Support for local MP4 files (self-hosted)
- [ ] Video thumbnail preview in teacher dashboard
- [ ] Analytics: track if students watched full video

---

## Questions?

See also:
- [CSV Formatting Rules](CSV_RULES.md)
- [Admin Documentation](ADMIN.md)
- [README](../README.md)
