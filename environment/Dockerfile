FROM osrf/ros@sha256:fa1d77aa0dea8632dd665498c5106a2a1db5a50e22d4bfd6ed5e21f2c37f3168
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 \
    LIBGL_ALWAYS_SOFTWARE=1 QT_X11_NO_MITSHM=1 ROS_MASTER_URI=http://127.0.0.1:11311

# The pinned desktop-full base already contains ROS and OpenCV. Only signed
# Ubuntu packages for numerical optimization and offline plots are needed.
RUN rm -f /etc/apt/sources.list.d/*.list && \
    printf 'deb http://archive.ubuntu.com/ubuntu xenial main universe\ndeb http://archive.ubuntu.com/ubuntu xenial-updates main universe\ndeb http://security.ubuntu.com/ubuntu xenial-security main universe\n' > /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential cmake libatlas-base-dev libeigen3-dev \
      libgoogle-glog-dev libsuitesparse-dev python-numpy python-matplotlib \
      python-yaml && \
    rm -rf /var/lib/apt/lists/*

COPY repro/cache/ceres-1.14.0.tar.gz /tmp/ceres.tar.gz
RUN echo '1296330fcf1e09e6c2f926301916f64d4a4c5c0ff12d460a9bc5d4c48411518f  /tmp/ceres.tar.gz' | sha256sum -c - && \
    mkdir /tmp/ceres && tar -xzf /tmp/ceres.tar.gz -C /tmp/ceres --strip-components=1 && \
    mkdir /tmp/ceres/build && cd /tmp/ceres/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DBUILD_EXAMPLES=OFF && \
    make -j4 && make install && ldconfig && rm -rf /tmp/ceres /tmp/ceres.tar.gz


WORKDIR /work
ENTRYPOINT ["/bin/bash"]
CMD ["-c", "source /opt/ros/kinetic/setup.bash; exec bash"]
