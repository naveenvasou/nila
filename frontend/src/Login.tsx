import { useState } from 'react';
import axios from 'axios';
import { API_URL } from './config';
import { useNavigate, Link } from 'react-router-dom';

export default function Login() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await axios.post(`${API_URL}/token`, formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            localStorage.setItem('token', response.data.access_token);
            navigate('/chat');
        } catch (err) {
            if (axios.isAxiosError(err)) {
                setError('Invalid username or password');
            } else {
                setError('Login failed');
            }
        }
    };

    return (
        <div className="flex justify-center items-center h-screen bg-warm-bg font-sans">
            <div className="bg-white p-8 rounded-2xl shadow-lg w-full max-w-sm">
                <h2 className="text-2xl font-bold text-nila-text mb-6 text-center">Login to Nila</h2>
                {error && <p className="text-red-500 text-sm mb-4 text-center">{error}</p>}
                <form onSubmit={handleLogin} className="flex flex-col gap-4">
                    <input
                        type="text"
                        placeholder="Username"
                        className="p-3 border rounded-lg outline-none focus:border-sage-accent"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        className="p-3 border rounded-lg outline-none focus:border-sage-accent"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    <button
                        type="submit"
                        className="bg-wheat-bubble text-nila-text font-semibold py-3 rounded-lg hover:bg-sage-accent hover:text-white transition-colors"
                    >
                        Sign In
                    </button>
                </form>
                <p className="mt-4 text-center text-sm text-nila-subtext">
                    Don't have an account? <Link to="/register" className="text-sage-accent hover:underline">Register</Link>
                </p>
            </div>
        </div>
    );
}
