"""Unit tests for RefreshTokenService."""

import pytest

from app.infrastructure.security.random_hex_token_service import RandomHEXTokenService


class TestRefreshTokenService:
    def test_generate_returns_hex_string(self):
        """Test token generation returns hex string of correct length."""
        service = RandomHEXTokenService(token_length=32)
        token = service.generate()
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes = 64 hex chars
        assert all(c in "0123456789abcdef" for c in token)

    def test_generate_returns_unique_tokens(self):
        """Test each generation produces unique token."""
        service = RandomHEXTokenService(token_length=32)
        tokens = [service.generate() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_hash_returns_sha256(self):
        """Test hash returns SHA-256 hex string."""
        service = RandomHEXTokenService()
        token = "test_token_12345"
        token_hash = service.hash(token)
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64  # SHA-256 = 64 hex chars

    def test_hash_is_deterministic(self):
        """Test same token always produces same hash."""
        service = RandomHEXTokenService()
        token = "test_token_12345"
        hash1 = service.hash(token)
        hash2 = service.hash(token)
        assert hash1 == hash2

    def test_verify_succeeds_for_matching_token(self):
        """Test verify returns True for matching token."""
        service = RandomHEXTokenService()
        token = service.generate()
        token_hash = service.hash(token)
        assert service.verify(token, token_hash) is True

    def test_verify_fails_for_different_token(self):
        """Test verify returns False for different token."""
        service = RandomHEXTokenService()
        token1 = service.generate()
        token2 = service.generate()
        token_hash = service.hash(token1)
        assert service.verify(token2, token_hash) is False

    def test_token_length_validation(self):
        """Test token length must be >= 16 bytes."""
        with pytest.raises(ValueError, match="Token length must be >= 16"):
            RandomHEXTokenService(token_length=8)

    def test_custom_token_length(self):
        """Test custom token length generates correct size."""
        service = RandomHEXTokenService(token_length=16)
        token = service.generate()
        assert len(token) == 32  # 16 bytes = 32 hex chars

    def test_hash_different_for_different_tokens(self):
        """Test different tokens produce different hashes."""
        service = RandomHEXTokenService()
        token1 = "token1"
        token2 = "token2"
        hash1 = service.hash(token1)
        hash2 = service.hash(token2)
        assert hash1 != hash2
