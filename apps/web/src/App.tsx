import { useState } from 'react';
import { InputPanel } from './components/InputPanel';
import { Reader } from './components/Reader';

function App() {
  const [activeChapterId, setActiveChapterId] = useState<string | null>(null);
  const [pages, setPages] = useState<string[]>([]);

  const handleComplete = (chapterId: string, chapterPages: string[]) => {
    setActiveChapterId(chapterId);
    setPages(chapterPages);
  };

  return (
    <div className="App" style={{ padding: '1rem', fontFamily: 'sans-serif' }}>
      <header style={{ marginBottom: '2rem' }}>
        <h1>Ogma Web Reader</h1>
      </header>
      
      {!activeChapterId ? (
        <InputPanel onComplete={handleComplete} />
      ) : (
        <div>
          <div style={{ marginBottom: '1rem' }}>
            <button onClick={() => setActiveChapterId(null)}>← Back to Download</button>
            <span style={{ marginLeft: '1rem' }}>Chapter: {activeChapterId}</span>
          </div>
          <Reader chapterId={activeChapterId} pages={pages} />
        </div>
      )}
    </div>
  );
}

export default App;
