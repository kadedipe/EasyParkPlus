"""
Response compression middleware.
"""

import gzip
import zlib
from typing import List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.responses import Response


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for compressing responses.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compressible_types: List[str] = None
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = compressible_types or [
            "text/plain",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "application/xml",
            "application/rss+xml",
            "image/svg+xml"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Compress response if client supports it and response is compressible.
        """
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        
        response = await call_next(request)
        
        # Don't compress if:
        # - Response is already compressed
        # - Response is too small
        # - Content type is not compressible
        # - Client doesn't accept compression
        if (
            "content-encoding" in response.headers or
            "content-length" in response.headers and
            int(response.headers["content-length"]) < self.minimum_size or
            not self._is_compressible(response.headers.get("content-type", "")) or
            not accept_encoding
        ):
            return response
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Compress based on accepted encoding
        if "gzip" in accept_encoding:
            compressed_body = self._compress_gzip(body)
            encoding = "gzip"
        elif "deflate" in accept_encoding:
            compressed_body = self._compress_deflate(body)
            encoding = "deflate"
        else:
            # No supported compression
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        
        # Create compressed response
        compressed_response = Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
        # Update headers
        compressed_response.headers["content-encoding"] = encoding
        compressed_response.headers["content-length"] = str(len(compressed_body))
        compressed_response.headers["vary"] = "Accept-Encoding"
        
        return compressed_response
    
    def _is_compressible(self, content_type: str) -> bool:
        """
        Check if content type is compressible.
        """
        content_type = content_type.split(";")[0].strip().lower()
        return any(
            compressible in content_type
            for compressible in self.compressible_types
        )
    
    def _compress_gzip(self, data: bytes) -> bytes:
        """
        Compress data using gzip.
        """
        return gzip.compress(data, compresslevel=9)
    
    def _compress_deflate(self, data: bytes) -> bytes:
        """
        Compress data using deflate.
        """
        return zlib.compress(data, level=9)


class BrotliCompressionMiddleware(BaseHTTPMiddleware):
    """
    Brotli compression middleware (better compression ratio).
    Requires brotli package: pip install brotli
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Compress response using Brotli if supported.
        """
        try:
            import brotli
        except ImportError:
            # Fall back to standard compression
            return await call_next(request)
        
        accept_encoding = request.headers.get("accept-encoding", "")
        
        if "br" not in accept_encoding:
            return await call_next(request)
        
        response = await call_next(request)
        
        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # Compress with Brotli
        compressed_body = brotli.compress(body, quality=11)
        
        # Create compressed response
        compressed_response = Response(
            content=compressed_body,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
        
        compressed_response.headers["content-encoding"] = "br"
        compressed_response.headers["content-length"] = str(len(compressed_body))
        compressed_response.headers["vary"] = "Accept-Encoding"
        
        return compressed_response