Create a sequence diagram for a user placing an order in an e-commerce system with the following flow:

1. **User** opens the checkout page in the **Web App**
2. **Web App** sends the order to the **API Gateway**
3. **API Gateway** validates the user's auth token with the **Auth Service**
4. **API Gateway** forwards the order to the **Order Service**
5. **Order Service** checks product availability with the **Inventory Service**
6. **Inventory Service** queries the **Inventory DB** and returns stock status
7. If items are in stock:
   - **Order Service** requests payment from the **Payment Service**
   - **Payment Service** processes the charge via external **Stripe API** and returns the result
   - **Order Service** saves the order to the **Order DB**
   - **Order Service** publishes an "order.created" event to the **Message Queue**
   - **Notification Service** consumes the event and sends a confirmation email
8. If items are out of stock:
   - **Order Service** returns an error to the user

Show all synchronous calls with request-response pairs. Use activate/deactivate blocks for processing. Distinguish synchronous calls from asynchronous messages to the queue.
