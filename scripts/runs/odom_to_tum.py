#!/usr/bin/env python3
import rospy
from nav_msgs.msg import Odometry

outfile = None

def cb(msg):
    t = msg.header.stamp.to_sec()
    p = msg.pose.pose.position
    q = msg.pose.pose.orientation
    outfile.write(f"{t:.9f} {p.x} {p.y} {p.z} {q.x} {q.y} {q.z} {q.w}\n")
    outfile.flush()

if __name__ == "__main__":
    rospy.init_node("odom_to_tum")
    topic = rospy.get_param("~topic", "/rovio/odometry")
    path = rospy.get_param("~out", "/tmp/rovio_traj.txt")
    outfile = open(path, "w")
    rospy.Subscriber(topic, Odometry, cb, queue_size=1000)
    rospy.spin()
