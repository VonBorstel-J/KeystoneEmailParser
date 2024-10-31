// static/components/ParsingOverlay/ParserForm.jsx
import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { parseEmail } from '../../js/actions/parsingActions';

const ParserForm = () => {
  const dispatch = useDispatch();
  const socket = useSelector((state) => state.socket.socket);

  const [formData, setFormData] = useState({
    emailContent: '',
    parserOption: '',
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // Dispatch parseEmail action
    dispatch(parseEmail(formData, socket));
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label>Email Content:</label>
        <textarea
          name="emailContent"
          value={formData.emailContent}
          onChange={handleInputChange}
        />
      </div>
      <div>
        <label>Parser Option:</label>
        <select
          name="parserOption"
          value={formData.parserOption}
          onChange={handleInputChange}
        >
          <option value="">Select a parser</option>
          <option value="enhanced">Enhanced Parser</option>
          <option value="composite">Composite Parser</option>
        </select>
      </div>
      <button type="submit">Parse Email</button>
    </form>
  );
};

export default ParserForm;
