FROM openjdk:latest
COPY . /usr/src/myapp
WORKDIR /usr/src/myapp
ADD resolv.conf /etc/resolv.conf

RUN rpm -ivh /usr/src/myapp/36558113.mysql-connector-java-8.0.19-1.el6.noarch.rpm
RUN javac Main.java

CMD ["java", "Main"]
