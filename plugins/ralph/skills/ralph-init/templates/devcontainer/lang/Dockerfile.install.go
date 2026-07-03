# ---- Language Runtime (from multi-stage) ----
COPY --from=golang /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"