# Popular Images Implementation Ideas

## Current Implementation
- Shows 6 most recent images (placeholder)
- Simple and works without additional data

## Future Implementation Options

### 1. View/Click Tracking
Track how many times images are viewed or clicked:

```javascript
// Add to image data structure
{
    id: 'img_123',
    viewCount: 45,
    clickCount: 12,
    generateSameCount: 5  // How many times "生成同款" was clicked
}

// Popular logic
case 'popular':
    filteredData = galleryData
        .sort((a, b) => (b.viewCount + b.clickCount * 2) - (a.viewCount + a.clickCount * 2))
        .slice(0, 10);
    break;
```

### 2. Time-Weighted Popularity
Newer images get a boost, but older popular ones still rank high:

```javascript
case 'popular':
    const now = Date.now();
    filteredData = galleryData
        .map(img => ({
            ...img,
            popularityScore: calculatePopularityScore(img, now)
        }))
        .sort((a, b) => b.popularityScore - a.popularityScore)
        .slice(0, 10);
    break;

function calculatePopularityScore(img, currentTime) {
    const ageInDays = (currentTime - img.timestamp) / (1000 * 60 * 60 * 24);
    const ageFactor = Math.max(0.1, 1 - (ageInDays / 30)); // Decay over 30 days
    
    return (img.viewCount || 0) * ageFactor + 
           (img.clickCount || 0) * 2 * ageFactor + 
           (img.generateSameCount || 0) * 5 * ageFactor;
}
```

### 3. User Engagement Metrics
Track different types of user interactions:

```javascript
// Enhanced image data
{
    id: 'img_123',
    metrics: {
        views: 120,
        generateSame: 15,    // "生成同款" clicks
        timeSpent: 4500,     // Total ms users spent viewing
        shares: 3,           // If sharing feature exists
        likes: 25            // If like feature exists
    }
}

// Weighted popularity calculation
case 'popular':
    filteredData = galleryData
        .map(img => ({
            ...img,
            score: calculateEngagementScore(img.metrics)
        }))
        .sort((a, b) => b.score - a.score)
        .slice(0, 10);
    break;

function calculateEngagementScore(metrics) {
    return (
        (metrics.views || 0) * 1 +
        (metrics.generateSame || 0) * 10 +  // High value action
        (metrics.timeSpent || 0) / 1000 * 2 +
        (metrics.shares || 0) * 15 +
        (metrics.likes || 0) * 5
    );
}
```

### 4. Prompt Similarity Clustering
Group similar prompts and show the best example from each cluster:

```javascript
case 'popular':
    const clusters = clusterByPromptSimilarity(galleryData);
    filteredData = clusters
        .map(cluster => cluster.sort((a, b) => b.score - a.score)[0]) // Best from each cluster
        .sort((a, b) => b.score - a.score)
        .slice(0, 10);
    break;
```

### 5. Server-Side Analytics
Let the backend calculate popularity:

```javascript
case 'popular':
    // API call to get popular images
    const response = await fetch(`${API_BASE_URL}/v1/gallery/popular`);
    const popularData = await response.json();
    filteredData = popularData.images;
    break;
```

## Recommended Implementation Path

### Phase 1 (Current)
✅ Show most recent images as "popular"

### Phase 2 (Next)
- Add view tracking to images
- Track "生成同款" button clicks
- Simple popularity = views + clicks * 5

### Phase 3 (Advanced)
- Time-weighted scoring
- Multiple engagement metrics
- Server-side analytics

### Phase 4 (Future)
- Machine learning recommendations
- User preference learning
- A/B testing for popularity algorithms

## Implementation Notes

### Adding View Tracking
```javascript
// In createGalleryItem function
img.addEventListener('click', () => {
    trackImageView(item.id);
});

// Track generate same clicks
generateSameBtn.addEventListener('click', () => {
    trackGenerateSame(item.id);
});
```

### Local Storage Tracking (Simple)
```javascript
function trackImageView(imageId) {
    const views = JSON.parse(localStorage.getItem('imageViews') || '{}');
    views[imageId] = (views[imageId] || 0) + 1;
    localStorage.setItem('imageViews', JSON.stringify(views));
}
```

### Server-Side Tracking (Better)
```javascript
function trackImageView(imageId) {
    fetch(`${API_BASE_URL}/v1/analytics/view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ imageId, timestamp: Date.now() })
    });
}
```

The key is to start simple and gradually add more sophisticated metrics as you gather data about user behavior! 