import React, { useState, useEffect, useCallback, useRef } from 'react';
import { FeedConfig, NewsItem, ProcessingStatus } from './types';
import { fetchFeed } from './services/rssService';
import { analyzeNewsItem } from './services/geminiService';
import NewsCard from './components/NewsCard';
import DashboardHeader from './components/DashboardHeader';

// Feed Configurations
const FEEDS: FeedConfig[] = [
  { id: 'techcrunch', name: 'TechCrunch AI', url: 'https://techcrunch.com/category/artificial-intelligence/feed/', color: '#16a34a' }, // Green
  { id: 'openai', name: 'OpenAI Blog', url: 'https://openai.com/index.xml', color: '#000000' }, // Black (Rendered as white/grey in dark mode)
  { id: 'deepmind', name: 'Google DeepMind', url: 'https://deepmind.google/rss/blog', color: '#4285F4' }, // Google Blue
];

const REFRESH_INTERVAL = 15 * 60 * 1000; // 15 minutes

const App: React.FC = () => {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [nextUpdate, setNextUpdate] = useState<Date>(new Date(Date.now() + REFRESH_INTERVAL));
  const processingQueueRef = useRef<Set<string>>(new Set());

  // Function to process a single item with Gemini
  const processItem = useCallback(async (item: NewsItem) => {
    // If already processing or completed, skip
    if (processingQueueRef.current.has(item.id) || item.status === ProcessingStatus.COMPLETED) return;

    processingQueueRef.current.add(item.id);
    
    // Update status to PROCESSING UI
    setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: ProcessingStatus.PROCESSING } : i));

    try {
      const result = await analyzeNewsItem(item.originalTitle, item.originalContent);
      
      setItems(prev => prev.map(i => {
        if (i.id === item.id) {
          return {
            ...i,
            status: ProcessingStatus.COMPLETED,
            translatedTitle: result.translatedTitle,
            summary: result.summary,
          };
        }
        return i;
      }));
    } catch (error) {
      console.error(`Failed to process item ${item.id}`, error);
      setItems(prev => prev.map(i => i.id === item.id ? { ...i, status: ProcessingStatus.FAILED } : i));
    } finally {
      processingQueueRef.current.delete(item.id);
    }
  }, []);

  // Main refresh logic
  const refreshFeeds = useCallback(async () => {
    if (isLoading) return;
    setIsLoading(true);

    try {
      const promises = FEEDS.map(feed => fetchFeed(feed));
      const results = await Promise.all(promises);
      const fetchedItems = results.flat();

      // Sort by date desc
      fetchedItems.sort((a, b) => b.pubDate.getTime() - a.pubDate.getTime());

      setItems(prevItems => {
        // Explicitly cast to tuple to ensure correct Map type inference
        const newItemsMap = new Map(fetchedItems.map(i => [i.id, i] as [string, NewsItem]));
        const existingItemsMap = new Map(prevItems.map(i => [i.id, i] as [string, NewsItem]));
        
        const merged: NewsItem[] = [];
        let hasNewHighPriority = false;

        // Merge logic: Keep existing if already processed, otherwise use new
        for (const [id, newItem] of newItemsMap) {
          if (existingItemsMap.has(id)) {
            const existing = existingItemsMap.get(id)!;
            // Keep existing state but update isNew if logic requires (e.g., if it was seen before, it's not "new" anymore ideally, but let's keep simple)
            merged.push(existing);
          } else {
            // Truly new item
            newItem.isNew = true;
            merged.push(newItem);
            hasNewHighPriority = true;
          }
        }

        // Clean up old items not in feed anymore? 
        // For a dashboard, we might want to keep them, but let's limit to top 30 to prevent memory leak
        const final = merged.sort((a, b) => b.pubDate.getTime() - a.pubDate.getTime()).slice(0, 30);
        
        if (hasNewHighPriority && "Notification" in window && Notification.permission === "granted") {
           new Notification("새로운 AI 뉴스", { body: "새로운 뉴스가 업데이트 되었습니다." });
        }

        return final;
      });

      setLastUpdated(new Date());
      setNextUpdate(new Date(Date.now() + REFRESH_INTERVAL));

    } catch (error) {
      console.error("Refresh failed", error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  // Initial Load & Interval
  useEffect(() => {
    refreshFeeds();
    
    const intervalId = setInterval(refreshFeeds, REFRESH_INTERVAL);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only mount

  // Watch items for pending processing
  useEffect(() => {
    const pendingItems = items.filter(i => i.status === ProcessingStatus.PENDING);
    // Process one by one or in small batches to be nice to the API
    // We initiate all, but the browser/network limits concurrency naturally. 
    // Gemini rate limits might be an issue, so we could throttle, but for this demo we'll fire.
    pendingItems.forEach(item => {
      processItem(item);
    });
  }, [items, processItem]);

  return (
    <div className="min-h-screen bg-gray-950 text-slate-200 font-sans">
      <DashboardHeader 
        lastUpdated={lastUpdated} 
        nextUpdate={nextUpdate} 
        onRefresh={refreshFeeds}
        isLoading={isLoading}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Source Legend */}
        <div className="flex flex-wrap gap-4 mb-8">
          {FEEDS.map(feed => (
            <div key={feed.id} className="flex items-center gap-2 text-sm bg-gray-900 px-3 py-1.5 rounded-full border border-gray-800">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: feed.color }}></span>
              <span className="text-gray-400">{feed.name}</span>
            </div>
          ))}
        </div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map(item => {
            const feedConfig = FEEDS.find(f => f.id === item.sourceId);
            return (
              <NewsCard 
                key={item.id} 
                item={item} 
                sourceConfig={feedConfig} 
                onAnalyze={processItem}
              />
            );
          })}
        </div>

        {/* Empty State */}
        {!isLoading && items.length === 0 && (
          <div className="text-center py-20">
             <div className="inline-block p-4 rounded-full bg-gray-900 mb-4 text-gray-600">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
             </div>
             <p className="text-gray-500 text-lg">뉴스를 가져오는 중입니다...</p>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
