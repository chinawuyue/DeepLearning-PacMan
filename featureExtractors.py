# featureExtractors.py
# --------------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


"Feature extractors for Pacman game states"
import itertools

from game import Directions, Actions
import util
import numpy as np

class FeatureExtractor:
    def getFeatures(self, state, action):
        """
          Returns a dict from features to counts
          Usually, the count will just be 1.0 for
          indicator functions.
        """
        util.raiseNotDefined()

class IdentityExtractor(FeatureExtractor):
    def getFeatures(self, state, action):
        feats = util.Counter()
        feats[(state,action)] = 1.0
        return feats

class CoordinateExtractor(FeatureExtractor):
    def getFeatures(self, state, action):
        feats = util.Counter()
        feats[state] = 1.0
        feats['x=%d' % state[0]] = 1.0
        feats['y=%d' % state[0]] = 1.0
        feats['action=%s' % action] = 1.0
        return feats

def closestFood(pos, food, walls):
    """
    closestFood -- this is similar to the function that we have
    worked on in the search project; here its all in one place
    """
    fringe = [(pos[0], pos[1], 0)]
    expanded = set()
    while fringe:
        pos_x, pos_y, dist = fringe.pop(0)
        if (pos_x, pos_y) in expanded:
            continue
        expanded.add((pos_x, pos_y))
        # if we find a food at this location then exit
        if food[pos_x][pos_y]:
            return dist, (pos_x, pos_y)
        # otherwise spread out from the location to its neighbours
        nbrs = Actions.getLegalNeighbors((pos_x, pos_y), walls)
        for nbr_x, nbr_y in nbrs:
            fringe.append((nbr_x, nbr_y, dist+1))
    # no food found
    return None

class SimpleExtractor(FeatureExtractor):
    """
    Returns simple features for a basic reflex Pacman:
    - whether food will be eaten
    - how far away the next food is
    - whether a ghost collision is imminent
    - whether a ghost is one step away
    """

    def getFeatures(self, state, action):
        # extract the grid of food and wall locations and get the ghost locations
        food = state.getFood()
        walls = state.getWalls()
        ghosts = state.getGhostPositions()

        features = util.Counter()

        features["bias"] = 1.0

        # compute the location of pacman after he takes the action
        x, y = state.getPacmanPosition()
        dx, dy = Actions.directionToVector(action)
        next_x, next_y = int(x + dx), int(y + dy)

        # count the number of ghosts 1-step away
        features["#-of-ghosts-1-step-away"] = sum((next_x, next_y) in Actions.getLegalNeighbors(g, walls) for g in ghosts)

        features["eats-food"] = 1.0 if not features["#-of-ghosts-1-step-away"] and food[next_x][next_y] else 0

        # if there is no danger of ghosts then add the food feature
        #if not features["#-of-ghosts-1-step-away"] and food[next_x][next_y]:
        #    features["eats-food"] = 1.0

        dist = closestFood((next_x, next_y), food, walls)[0]

        features["closest-food"] = float(dist) / (walls.width * walls.height) if dist is not None else 1

        # if dist is not None:
        #     # make the distance a number less than one otherwise the update
        #     # will diverge wildly
        #     features["closest-food"] = float(dist) / (walls.width * walls.height)
        features.divideAll(10.0)
        return features

class SimpleListExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        qState = np.array(SimpleExtractor().getFeatures(state, action).values()).astype(dtype=float)
        return qState

class PositionsExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        pacmanPosition = np.array(state.getPacmanPosition()).flatten()
        ghostPositions = np.array(state.getGhostPositions()).flatten()

        return np.concatenate((ghostPositions, pacmanPosition)).astype(dtype=float)

class PositionsFoodWallsExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        pacmanPosition = np.array(state.getPacmanPosition()).flatten()
        ghostPositions = np.array(state.getGhostPositions()).flatten()

        legalActions = getLegalActions(state)
        walls = np.array(state.getWalls().data).flatten()
        food = np.array([state.getFood().data]).flatten()

        return np.concatenate((pacmanPosition, ghostPositions, legalActions, walls, food)).astype(dtype=float)/20

class DistancesExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        x, y = state.getPacmanPosition()

        legalActions = getLegalActions(state)
        food = getFoodAroundPacman(state)

        distances = np.array([[x-gx, y-gy] for gx, gy in state.getGhostPositions()]).flatten()
        areGhostsScared = [s.scaredTimer > 0 for s in state.getGhostStates()]

        ghostDirections = [Directions.getIndex(s.getDirection()) for s in state.getGhostStates()]
        capsules = getCapsulesAroundPacman(state)

        qState = np.concatenate((distances, areGhostsScared, capsules, legalActions, food, ghostDirections)).astype(dtype=float)

        return qState/25

class ShortSightedBinaryExtractor(FeatureExtractor):

    def getFeatures(self, state, action):

        legalActions = getLegalActions(state)
        food = getFoodAroundPacman(state)

        ghostsNearby = getGhostsAroundPacman(state)
        areGhostsScared = [s.scaredTimer > 0 for s in state.getGhostStates()]

        ghostDirections = np.array([Directions.getIndex(s.getDirection()) for s in state.getGhostStates()])
        capsules = getCapsulesAroundPacman(state)

        qState = np.concatenate((ghostsNearby, areGhostsScared, capsules, legalActions, food, ghostDirections/4.0)).astype(dtype=float)
        return qState

class PositionsDirectionsExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        positionsState = np.array(PositionsExtractor().getFeatures(state, action))
        ghostDirections = np.array([Directions.getIndex(s.getDirection()) for s in state.getGhostStates()])

        legalActions = getLegalActions(state)
        legalActions = np.array([Directions.fromIndex(i) in legalActions for i in range(4)])

        return np.concatenate((positionsState, ghostDirections, legalActions)).astype(dtype=float)/100

class PositionsDirectionsFoodExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        positionsState = np.array(PositionsExtractor().getFeatures(state, action))
        ghostDirections = np.array([Directions.getIndex(s.getDirection()) for s in state.getGhostStates()])
        legalActions = getLegalActions(state)
        food = np.array(state.getFood().data).flatten()

        return np.concatenate((positionsState, ghostDirections, legalActions, food)).astype(dtype=float)/15

class PositionsDirectionsFoodWallsExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        positionsState = np.array(PositionsExtractor().getFeatures(state, action))
        ghostDirections = np.array([Directions.getIndex(s.getDirection()) for s in state.getGhostStates()])
        walls = np.array(state.getWalls().data).flatten()
        food = np.array(state.getFood().data).flatten()

        return np.concatenate((positionsState/15, ghostDirections/4, walls, food)).astype(dtype=float)

class CollisionExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        pacmanPosition = state.getPacmanPosition()
        ghostPositions = state.getGhostPositions()
        legalActions = [] #np.array([Directions.fromIndex(i) in state.getLegalActions() for i in range(5)])

        distances = np.array([[pos[0] - pacmanPosition[0], pos[1] - pacmanPosition[1]] for pos in ghostPositions]).flatten()
        qState = np.concatenate((distances, legalActions)).astype(dtype=float)

        return qState

class MatricesExtractor(FeatureExtractor):

    def getFeatures(self, state, action):

        def getWallMatrix(state):
            """ Return matrix with wall coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            grid = state.data.layout.walls
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for i in range(grid.height):
                for j in range(grid.width):
                    # Put cell vertically reversed in matrix
                    cell = 1 if grid[j][i] else 0
                    matrix[-1 - i][j] = cell
            return matrix

        def getPacmanMatrix(state):
            """ Return matrix with pacman coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for agentState in state.data.agentStates:
                if agentState.isPacman:
                    pos = agentState.configuration.getPosition()
                    cell = 1
                    matrix[-1 - int(pos[1])][int(pos[0])] = cell

            return matrix

        def getGhostMatrix(state):
            """ Return matrix with ghost coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for agentState in state.data.agentStates:
                if not agentState.isPacman:
                    if not agentState.scaredTimer > 0:
                        pos = agentState.configuration.getPosition()
                        cell = 1
                        matrix[-1 - int(pos[1])][int(pos[0])] = cell

            return matrix

        def getScaredGhostMatrix(state):
            """ Return matrix with ghost coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for agentState in state.data.agentStates:
                if not agentState.isPacman:
                    if agentState.scaredTimer > 0:
                        pos = agentState.configuration.getPosition()
                        cell = 1
                        matrix[-1 - int(pos[1])][int(pos[0])] = cell

            return matrix

        def getFoodMatrix(state):
            """ Return matrix with food coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            grid = state.data.food
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for i in range(grid.height):
                for j in range(grid.width):
                    # Put cell vertically reversed in matrix
                    cell = 1 if grid[j][i] else 0
                    matrix[-1 - i][j] = cell

            return matrix

        def getCapsulesMatrix(state):
            """ Return matrix with capsule coordinates set to 1 """
            width, height = state.data.layout.width, state.data.layout.height
            capsules = state.data.layout.capsules
            matrix = np.zeros((height, width))
            matrix.dtype = int

            for i in capsules:
                # Insert capsule cells vertically reversed into matrix
                matrix[-1 - i[1], i[0]] = 1

            return matrix

        # Create observation matrix as a combination of
        # wall, pacman, ghost, food and capsule matrices
        # width, height = state.data.layout.width, state.data.layout.height
        width, height = state.data.layout.width, state.data.layout.height
        observation = np.zeros((6, height, width))

        observation[0] = getWallMatrix(state)
        observation[1] = getPacmanMatrix(state)
        observation[2] = getGhostMatrix(state)
        #observation[3] = getScaredGhostMatrix(state)
        observation[4] = getFoodMatrix(state)
        #observation[5] = getCapsulesMatrix(state)

        observation = np.swapaxes(observation, 0, 2).flatten()

        #legalActions = getLegalActioins(state)
        #legalActions = np.array([Directions.fromIndex(i) in legalActions for i in range(5)])

        return observation.astype(dtype=float)

class DangerousActionsExtractor(FeatureExtractor):

    def getFeatures(self, state, action):
        from pacmanAgents import CarefulGreedyAgent

        dangerousActions = CarefulGreedyAgent()._getAction(state)[1]
        dangerousActionsBools = np.array([action in dangerousActions for action in Directions.asList() if action != Directions.STOP]).astype(float)
        legalActions = getLegalActions(state)

        return np.concatenate((dangerousActionsBools, legalActions)).astype(dtype=float)

def getLegalActions(state):
    legalActions = state.getLegalActions()
    if Directions.STOP in legalActions: legalActions.remove(Directions.STOP)
    return np.array([Directions.fromIndex(i) in legalActions for i in range(4)])

def getFoodAroundPacman(state):

    x, y = state.getPacmanPosition()
    foodMatrix = state.getFood()
    return np.array([foodMatrix[x+dx][y+dy] for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)]])

def getCapsulesAroundPacman(state):

    x, y = state.getPacmanPosition()
    remainingCapsules = state.getCapsules()
    return np.array([(x+dx, y+dy) in remainingCapsules for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)]])

def getGhostsAroundPacman(state):

    ghostPositions = state.getGhostPositions()
    x, y = state.getPacmanPosition()
    ghostsNearby = [0] * 4

    thresh = 2.0
    for ghostX, ghostY in ghostPositions:

        dx = ghostX-x
        dy = ghostY-y

        if abs(dx) <= thresh and dy == 0:
            if dx < 0:
                ghostsNearby[0] = 1
            else:
                ghostsNearby[1] = 1

        if abs(dy) <= thresh and dx == 0:
            if dy < 0:
                ghostsNearby[2] = 1
            else:
                ghostsNearby[3] = 1

    return ghostsNearby
