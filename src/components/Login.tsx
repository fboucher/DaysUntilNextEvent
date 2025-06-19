import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Container, Form, Button, Alert } from 'react-bootstrap';

const lightBulbImages = [
  require('../assets/lightbulbs/bulb1.png'),
  require('../assets/lightbulbs/bulb2.png'),
  require('../assets/lightbulbs/bulb3.png'),
  // Add more images as needed
];

function getRandomBulbImage() {
  const idx = Math.floor(Math.random() * lightBulbImages.length);
  return lightBulbImages[idx];
}

const Login: React.FC = () => {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [bulbImage] = React.useState(getRandomBulbImage());
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setError('');
      setLoading(true);
      await login(email, password);
    } catch {
      setError('Failed to log in');
    }

    setLoading(false);
  };

  return (
    <Container>
      <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
        <div className="w-100" style={{ maxWidth: '400px' }}>
          <h2 className="text-center mb-4">Log In</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={handleSubmit}>
            <Form.Group id="email" className="mb-3">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Form.Group>
            <Form.Group id="password" className="mb-3">
              <Form.Label>Password</Form.Label>
              <Form.Control
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Form.Group>
            <Button disabled={loading} className="w-100" type="submit">
              {loading ? 'Loading...' : 'Log In'}
            </Button>
          </Form>
          <div className="text-center mt-3">
            <Link to="/forgot-password">Forgot Password?</Link>
          </div>
          <div className="text-center mt-2">
            Need an account? <Link to="/signup">Sign Up</Link>
          </div>
        </div>
      </div>
      <div className="text-center">
        <img src={bulbImage} alt="Random Light Bulb" style={{ width: 100, height: 100 }} />
      </div>
    </Container>
  );
};

export default Login;