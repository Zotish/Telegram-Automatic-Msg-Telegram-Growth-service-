import React, { useState } from 'react';
import axios from 'axios';





const API = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

function OTPModal({ phone, onClose }) {
  const [otp, setOtp] = useState('');

  const handleVerify = async () => {
    try {
      const res = await axios.post(`${API}/auth/verify-otp`, { phone, otp });
      if (res.data.status === "SUCCESS") {
        alert("Login Successful!");
        onClose();
      } else {
        alert("Invalid OTP: " + res.data.message);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
      <div className="bg-white p-8 rounded-lg shadow-xl w-96">
        <h3 className="text-xl font-bold mb-4">Enter OTP for {phone}</h3>
        <p className="text-sm text-gray-500 mb-4">Check your Telegram app for the code.</p>
        <input 
          type="text" 
          className="w-full border p-2 mb-4 rounded" 
          placeholder="5-digit code"
          onChange={(e) => setOtp(e.target.value)}
        />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-gray-600">Cancel</button>
          <button onClick={handleVerify} className="px-4 py-2 bg-green-600 text-white rounded">Verify</button>
        </div>
      </div>
    </div>
  );
}
