# Where the target is relative to the frame center (rpi5os vision).
# dx, dy in [-1, 1]: -1 is the left / top edge, 0 the center, 1 the right / bottom edge.
std_msgs/Header header
bool detected
float32 confidence
float32 dx
float32 dy
# Box area as a share of the frame, 0..1.
float32 area
string class_name
