#!/usr/bin/env python3
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped

outfile = None

def cb(msg):
    t = msg.header.stamp.to_sec()
    p = msg.pose.pose.position
    q = msg.pose.pose.orientation
    outfile.write(f"{t:.9f} {p.x} {p.y} {p.z} {q.x} {q.y} {q.z} {q.w}\n")
    outfile.flush()

if __name__ == "__main__":
    rospy.init_node("pose_to_tum")
    topic = rospy.get_param("~topic", "/svo/pose_imu")
    path = rospy.get_param("~out", "/tmp/svo_traj.txt")
    outfile = open(path, "w")
    rospy.Subscriber(topic, PoseWithCovarianceStamped, cb, queue_size=1000)
    rospy.spin()
