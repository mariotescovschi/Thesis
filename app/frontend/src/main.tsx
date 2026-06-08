import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@exuanbo/file-icons-js/dist/css/file-icons.min.css';
import './app/theme.css';
import { Providers } from './app/providers';
import { App } from './app/App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
);
