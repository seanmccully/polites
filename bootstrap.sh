#!/bin/bash
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.


TOP_DIR=$(cd $(dirname "$0") && pwd)
USER=$(whoami)

VERSION=2.0.0
CASSANDRA_VERSION=cassandra-$VERSION
BACKUP_DIR=/mnt/backup
INSTALL_PATH=/var/lib/cassandra
LOG_PATH=/var/log/cassandra
CASSANDRA_URL=http://apache.mirrors.hoobly.com/cassandra/$VERSION/apache-$CASSANDRA_VERSION-bin.tar.gz
PIP_URL=https://pypi.python.org/packages/source/p/pip/pip-1.4.1.tar.gz
OUT_TO_ERR=2>/dev/null

YUM_JAVA=java-1.7.0-openjdk
APT_JAVA=openjdk-7-jre
ZYPPER_JAVA=java-1_7_0-openjdk
PACMAN_JAVA=jre7-openjdk

if [ ! `which java $OUT_TO_ERR ` ]; then 
   if [ `which yum $OUT_TO_ERR ` ]; then
   	sudo yum install -y $YUM_JAVA python python-setuptools python-devel gcc tar
   elif [ `which apt-get $OUT_TO_ERR ` ]; then
   	sudo apt-get install -y $APT_JAVA python python-setuptools python-dev gcc tar
   elif [ `which zypper $OUT_TO_ERR ` ]; then
	sudo zypper --non-interactive $ZYPPER_JAVA
   elif [ `which pacman $OUT_TO_ERR ` ]; then
	sudo pacman -S --noconfirm $PACMAN_JAVA python python-setuptools gcc-multilib
   fi
fi


cd $TOP_DIR;
mkdir -p tmp;
cd tmp;
curl -O $PIP_URL;
tar xvfz pip-1.4.1.tar.gz;
cd pip-1.4.1;
sudo python setup.py install;
cd ..;
sudo pip install -r $TOP_DIR/requirements.txt;
curl -O $CASSANDRA_URL;
tar xvfz apache-$CASSANDRA_VERSION-bin.tar.gz;
cd apache-$CASSANDRA_VERSION;
sudo mkdir -p $INSTALL_PATH;
sudo mkdir -p $LOG_PATH;
sudo mkdir -p $BACKUP_DIR
sudo chown -R $USER $INSTALL_PATH;
sudo chown -R $USER $LOG_PATH;
sudo chown -R $USER $BACKUP_DIR
cp -R * $INSTALL_PATH;
cd ../..;
cp settings/stop-server $INSTALL_PATH/bin/stop-server
sudo rm -rf tmp;
sudo python setup.py install
