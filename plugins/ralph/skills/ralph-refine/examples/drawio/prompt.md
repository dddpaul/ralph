Create a system architecture diagram for an e-commerce platform with the following components:

- **Web Frontend** — React SPA served via CDN
- **API Gateway** — routes requests, handles authentication
- **User Service** — manages user accounts and profiles (PostgreSQL database)
- **Product Catalog Service** — product listings and search (Elasticsearch + PostgreSQL)
- **Order Service** — order processing and history (PostgreSQL database)
- **Payment Service** — integrates with external payment provider (Stripe)
- **Notification Service** — sends emails and push notifications (connects to external email provider)
- **Message Queue** — RabbitMQ for async communication between services

Show all connections between components with labeled protocols (HTTP, gRPC, AMQP). Include the external systems (CDN, Stripe, Email Provider) as cloud shapes.
