"""
Dedicated endpoint for uploading a CA certificate bundle.

Uploaded files are stored in usr/certs/ (persisted via Docker named volume)
and the absolute in-container path is returned so the UI can populate the
tls_ca_bundle setting automatically.
"""
import os
from python.helpers.api import ApiHandler, Request, Response
from python.helpers import files
from python.helpers.security import safe_filename


class UploadCert(ApiHandler):
    """Upload a PEM CA certificate bundle for TLS verification."""

    ALLOWED_EXTENSIONS = {"pem", "crt", "cer", "ca-bundle", "cert"}

    @classmethod
    def requires_auth(cls) -> bool:
        return True

    async def process(self, input: dict, request: Request) -> dict | Response:
        if "file" not in request.files:
            raise Exception("No file provided")

        file = request.files["file"]
        if not file or not file.filename:
            raise Exception("Empty file")

        filename = safe_filename(file.filename)
        if not filename:
            raise Exception("Invalid filename")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            raise Exception(
                f"File type '.{ext}' not allowed. "
                f"Accepted: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        # Ensure certs directory exists inside the container
        certs_dir = files.get_abs_path("usr", "certs")
        os.makedirs(certs_dir, exist_ok=True)

        dest = os.path.join(certs_dir, filename)
        file.save(dest)

        return {"path": dest, "filename": filename}
