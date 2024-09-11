import math
import numpy as np
class GridCells:
    # -----------------------------Define our raw print bed area
    RawBd_y = 582;  # mm of space in y-direction
    RawBd_x = 282;  # mm of space in x-direction

    # ---------------Define area of bed to be printed on.
    EdgeSpace_y = 5;  # mm of space from edge in both sides in y-direction
    EdgeSpace_x = 5;  # mm of space from edge in both sides in x-direction

    PrintBd_y = RawBd_y - (2 * EdgeSpace_y);  # Subtract edge spacing from Raw area
    PrintBd_x = RawBd_x - (2 * EdgeSpace_x);  # Subtract edge spacing from Raw area

    # -----------------------------Define shape size and spacing between experiments

    ExpSpacing_y = 2;  # space in mm between each experiment in y-direction
    ExpSpacing_x = 2;  # space in mm between each experiment in x-direction

    # =============================================================================
    # ---------------------CREATE GRID THAT HOLDS ACTUAL POSITIONS-----------------
    # =============================================================================
    Z = 2;  # in mm
    # Z movement will need to be defined by G-Code somehow
    xPos = 0;
    yPos = 0;


    PrntShape_y = 0;  # space in mm will be taken up by a print in y-direction
    PrntShape_x = 0;  # space in mm will be taken up by a print in x-direction


    def ExperimentalGrid(self, PrntShape_x, PrntShape_y):
        self.PrntShape_x = PrntShape_x;
        self.PrntShape_y =  PrntShape_y
        '''
        This function creates an array of zeros with dimensions of the possible
        experimental locations on the print bed.

        Once a location has been visited the zero should be replaced with a 1,
        or any other value.
        '''
        ExpColumns = math.floor(self.PrintBd_x / (PrntShape_x + self.ExpSpacing_x));
        # calculates lowest integer possible for rows

        ExpRows = math.floor(self.PrintBd_y / (PrntShape_y + self.ExpSpacing_y));
        # calculates lowest integer possible for columns

        # ------Create empty array to represent unvisited experimental locations
        ExpGrid = np.zeros((ExpRows, ExpColumns));

        return ExpRows, ExpColumns, ExpGrid

    def LocationMaker(self, ExpRows, ExpColumns):
        '''
    This function will create three arrays that house the actual X, Y, and Z
    coordinates of the experimental locations.

        '''
        PosGrid_x = np.zeros((ExpRows, ExpColumns));  # same dimensions as Exp Grid
        PosGrid_y = np.zeros((ExpRows, ExpColumns));  # same dimensions as Exp Grid
        PosGrid_z = np.zeros((ExpRows, ExpColumns));  # same dimensions as Exp Grid

        X_start = self.EdgeSpace_x;  # in mm
        Y_start = self.EdgeSpace_y;  # in mm

        ExpSpaceX = (self.PrntShape_x + self.ExpSpacing_x)  # the space each experiment needs
        ExpSpaceY = (self.PrntShape_y + self.ExpSpacing_y)  # the space each experiment needs

        for i in range(ExpRows):
            for j in range(ExpColumns):
                if j == 0:  # -----------------------------Column (x) loop
                    xPos = X_start
                    PosGrid_x[i, j] = xPos
                else:
                    xPos = (j * ExpSpaceX) + X_start
                    PosGrid_x[i, j] = xPos
                if i == 0:  # -------------------Row (y) Loop
                    yPos = Y_start
                    PosGrid_y[i, j] = yPos
                else:
                    yPos = (i * ExpSpaceY) + Y_start
                    PosGrid_y[i, j] = yPos

                PosGrid_z[i, j] = self.Z

        return PosGrid_x, PosGrid_y, PosGrid_z

    # x, y, z = LocationMaker(ExpRows, ExpColumns, PrintBd_x, PrntShape_y,
    #                         EdgeSpace_x, EdgeSpace_y, xPos, yPos, Z)
