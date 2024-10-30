// static/components/App.jsx
import React from 'react';
import Header from './common/Header.jsx';
import ParserForm from './ParsingOverlay/ParserForm.jsx'; 
import ParsingOverlay from './ParsingOverlay/index.jsx'; 
import ResultViewer from './ResultViewer/index.jsx';
import ToastContainer from './common/ToastContainer.jsx';
import Modal from './common/Modal.jsx';

const App = () => {
  return (
    <div className="bg-gray-50 min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <article className="space-y-6">
            <ParserForm />
          </article>
          <article className="space-y-6">
            <ResultViewer />
          </article>
        </section>
      </main>
      <ToastContainer />
      <Modal />
      <ParsingOverlay />
    </div>
  );
};

export default App;