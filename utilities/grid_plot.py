
import matplotlib.pyplot as plt
import os
import io
import random
from config import Config
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from utilities.grid_cells import GridCells


class GridPlot(object):

    grid_cells = None

    # def init_plot(x_range, y_range):
    #     fig, ax = plt.subplots()
    #     x_cm = (int)(x_range/10 + 1)
    #     y_cm = (int)(y_range/10 + 1)
    #     ax.set_xlim(0, x_cm)
    #     ax.set_ylim(0, y_cm)
    #     ax.set_xlabel('X')
    #     ax.set_ylabel('Y')
    #
    #     # Create grid lines
    #     for x in range(max(x_cm, y_cm)):
    #         ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
    #         ax.axhline(x, color='gray', linestyle='--', linewidth=0.5)
    #     buf = io.BytesIO()
    #     plt.savefig(buf, format='png')
    #     buf.seek(0)
    #     return buf
    #
    # def draw_grid(ax):
    #     x_cm = (int)(282/10 + 1)
    #     y_cm = (int)(582/10 + 1)
    #     ax.set_xlim(0, x_cm)
    #     ax.set_ylim(0, y_cm)
    #     ax.set_xlabel('X')
    #     ax.set_ylabel('Y')
    #
    #     # Create grid lines
    #     for x in range(max(x_cm, y_cm)):
    #         ax.axvline(x, color='gray', linestyle='--', linewidth=0.5)
    #         ax.axhline(x, color='gray', linestyle='--', linewidth=0.5)
    #
    #
    # def update_plot(x, y):
    #     fig, ax = plt.subplots()
    #
    #     draw_grid(ax)
    #
    #     # ax.plot(x, y, 'o-')
    #     ax.add_patch(Rectangle((1, 1), 2, 6))
    #     ax.add_patch(Rectangle((10, 20), 5, 10))
    #     ax.set_title('Dynamic Plot')
    #     buf = io.BytesIO()
    #     plt.savefig(buf, format='png')
    #     buf.seek(0)
    #     return buf

    pcpfig = "pcpfig"
    nrows = 0
    ncols = 0
    # cell id for the first printing
    starting_cell_id = -1


    Cellid = []
    Cellval = []
    CELL_DONE_COLOR =55
    def __init__(self, name = None):
        self.cell_y_starting = None
        self.cell_x_starting = None
        self.name = name
        self.starting_cell_id = -1
        self.grid_cells = GridCells()

    def init_plot(self, x_range, y_range, shape_x, shape_y):
        self.nrows, self.ncols, _ = self.grid_cells.ExperimentalGrid(shape_x, shape_y)

        self.cell_x_starting, self.cell_y_starting, cell_z_starting = self.grid_cells.LocationMaker(self.nrows, self.ncols)


        fig, ax = plt.subplots()
        #
        # draw markers
        data = np.zeros(self.nrows * self.ncols)
        self.Cellid.append(0)
        self.Cellval.append(0)
        data[self.Cellid] = self.Cellval
        data = np.ma.array(data.reshape((self.nrows, self.ncols)), mask=data==0)
        ax.imshow(data, cmap="Greens", origin="lower", vmin=0)

        # optionally add grid
        ax.set_xticks(np.arange(self.ncols+1)-0.5, minor=True)
        ax.set_yticks(np.arange(self.nrows+1)-0.5, minor=True)
        ax.grid(which="minor")
        ax.tick_params(which="minor", size=0)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        fig.savefig(f'./{self.pcpfig}.png')
        buf.seek(0)
        return buf

    def get_top_left_corner_pos_by_cell_id(self, cell_id):
        """
        :param cell_id: starting from 0
        :return: the absolute position of the top left corner of this cell id
        """
        rowth = cell_id//self.ncols
        colth = cell_id - rowth*self.ncols
        return self.cell_x_starting[0][colth], self.cell_y_starting[rowth][0]


    def set_starting_cell_id(self, cell_id):
        self.starting_cell_id = cell_id

    def get_cell_id(self):
        return self.starting_cell_id
    def calculate_cell_id(self, x_pos, y_pos):
        row_indx = 0
        col_indx = 0
        cell_widths = self.cell_x_starting[0]
        cell_heights =[]

        for y_starting_point in self.cell_y_starting:
            cell_heights.append(y_starting_point[0])

        for width in cell_widths:
            if x_pos <= width:
                break;
            if x_pos > width and col_indx+1 < len(cell_widths) and x_pos < cell_widths[col_indx+1]:
                break;
            col_indx = col_indx +1

        for height in cell_heights:
            if y_pos <= height:
                break;
            if y_pos > height and row_indx+1 < len(cell_heights) and y_pos < cell_heights[row_indx+1]:
                break;
            row_indx = row_indx +1

        return row_indx*self.nrows + col_indx


    def load_plot(self):
        if not os.path.exists(f'./{self.pcpfig}.png'):
            return None
        image = plt.imread(f'./{self.pcpfig}.png')
        buf = io.BytesIO()
        plt.imsave(buf, image, format='png')
        buf.seek(0)
        return buf

    def update_plot(self, cell_id):

        fig, ax = plt.subplots()

        # draw markers
        data = np.zeros(self.nrows * self.ncols)
        self.Cellid.append(cell_id)
        self.Cellval.append(self.CELL_DONE_COLOR)
        data[self.Cellid] = self.Cellval
        data = np.ma.array(data.reshape((self.nrows, self.ncols)), mask=data==0)
        ax.imshow(data, cmap="Greens", origin="lower", vmin=0)

        # optionally add grid
        ax.set_xticks(np.arange(self.ncols + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(self.nrows + 1) - 0.5, minor=True)
        ax.grid(which="minor")
        ax.tick_params(which="minor", size=0)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        fig.savefig(f'./{self.pcpfig}.png')
        buf.seek(0)
        return buf
