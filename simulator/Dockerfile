FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV SIM_MODE=history
CMD ["sh", "-c", "if [ \"$SIM_MODE\" = 'drip' ]; then python drip.py; else python generate_history.py --reset; fi"]
