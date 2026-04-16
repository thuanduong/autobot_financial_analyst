backend
python -m backend_cloud.main
python -m backend_cloud.main -exness
python -m backend_cloud.main -oanda


frontend
set TARGET_BROKER=exness && npm run dev
set TARGET_BROKER=oanda && npm run dev

