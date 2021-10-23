export PATH=$PATH:'/home/team3/3D-Binpacking-GUI/backend/algorithm/py3dbp/'
echo $PATH
gunicorn --bind 0.0.0.0:4003 wsgi:app