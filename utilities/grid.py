# import matplotlib.pyplot as plt
# import matplotlib.animation as animation
# import numpy as np
# from IPython import display

# # Initialize points and grid size
# points = []
# grid_size = 10
#
# # Create a figure and axis
# fig, ax = plt.subplots()
# ax.set_xlim(0, grid_size)
# ax.set_ylim(0, grid_size)
# ax.set_xlabel('X')
# ax.set_ylabel('Y')
#
# # Create grid lines
# for x in range(grid_size + 1):
#     ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
#     ax.axhline(x, color='gray', linestyle='--', linewidth=0.5)
#
# # Initialize scatter plot
# points, = ax.plot([], [], 'bo', markersize=8)
#
# def init():
#     """Initialize the scatter plot."""
#     points.set_data([], [])
#     return points,
#
# def update(frame):
#     """Update the plot with a new set of points."""
#     x = np.random.uniform(0, 10, frame + 1)
#     y = np.random.uniform(0, 10, frame + 1)
#     points.set_data(x, y)
#     return points,
#
# # Create an animation
# anim = animation.FuncAnimation(fig=fig, func=update, init_func=init, frames=40, interval=30, blit=True, repeat=False)
# video = anim.to_html5_video()
#
# # embedding for the video
# html = display.HTML(video)
#
# # draw the animation
# display.display(html)
# plt.show()
# plt.close()

import matplotlib.pyplot as plt
import numpy as np
import time

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_xlabel('X')
ax.set_ylabel('Y')

# Create grid lines
for x in range(11):
    ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
    ax.axhline(x, color='gray', linestyle='--', linewidth=0.5)

# Initialize scatter plot
scatter, = ax.plot([], [], 'bo', markersize=8)

# Initialize empty lists for points
x_data, y_data = [], []


def update_plot(x_new, y_new):
    """Update the scatter plot with new points."""
    x_data.append(x_new)
    y_data.append(y_new)
    scatter.set_data(x_data, y_data)
    plt.draw()  # Redraw the plot
    plt.pause(0.1)  # Pause to create animation effect


# Enable interactive mode
# plt.ion()

# Simulate receiving points
for _ in range(10):
    # Generate random points
    x_new = np.random.uniform(0, 10)
    y_new = np.random.uniform(0, 10)

    # Update the plot
    update_plot(x_new, y_new)

    # Simulate delay (e.g., receiving new data)
    # time.sleep(1)

# Keep the plot open after the loop
# plt.ioff()
plt.show()
