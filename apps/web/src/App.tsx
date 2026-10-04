
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { RootLayout } from './layouts/RootLayout';
import { Home } from './pages/Home';
import { Reader } from './pages/Reader';

function App() {
  return (
    <>
      <Toaster position="bottom-right" />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootLayout />}>
            <Route index element={<Home />} />
            <Route path="reader/:chapterId" element={<Reader />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
