# Optional Nginx Reverse Proxy

Use `default.conf` to terminate HTTPS and forward:
- `/api/*` -> backend (`backend:8000`)
- all other routes -> frontend (`frontend:3000`)

Mount certs to `/etc/nginx/certs`:
- `fullchain.pem`
- `privkey.pem`

Example run:
```bash
docker run --name ai-coo-proxy --network ai-coo_default -p 80:80 -p 443:443 \
  -v $(pwd)/docker/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro \
  -v /path/to/certs:/etc/nginx/certs:ro \
  nginx:1.27
```
