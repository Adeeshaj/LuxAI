import math, sys
from lux.game import Game
from lux.game_objects import Unit
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from random import randint

DIRECTIONS = Constants.DIRECTIONS
game_state = None

#my constants
LEVEL_TO_UNITS = { 
    "40": {"workers": 7, "carts":0, "research":11},
    "80": {"workers": 17, "carts":0, "research":39},
    "120": {"workers": 31, "carts":0, "research":98},
    "160": {"workers": 44, "carts":0, "research":200},
    "200": {"workers": 49, "carts":0, "research":200},
    "240": {"workers": 39, "carts":0, "research":200},
    "280": {"workers": 28, "carts":0, "research":200},
    "320": {"workers": 20, "carts":0, "research":200},
    "360": {"workers": 16, "carts":0, "research":0},
}
EVENING_LENGTH = 1


def get_random_direction(pos, direct_dic, width, height):
        DIRECTIONS = ['NORTH','WEST', 'EAST', 'SOUTH', 'CENTER']
        index = randint(0, 4)
        direction = DIRECTIONS[index]
        if(pos.x==0 and direction=='WEST'):
            return get_random_direction(pos, direct_dic, width, height)
        elif(pos.y==0 and direction=='NORTH'):
            return get_random_direction(pos, direct_dic, width, height)
        elif(pos.x==width-1 and direction=='EAST'):
            return get_random_direction(pos, direct_dic, width, height)
        elif(pos.y==height-1 and direction=='SOUTH'):
            return get_random_direction(pos, direct_dic, width, height)
        else:
            return direct_dic[direction]

def get_resource_tiles(width, height, coal_researched, uranium_researched):
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                if (cell.resource.type == "coal" and not coal_researched): continue
                if (cell.resource.type == "uranium" and not uranium_researched): continue
                resource_tiles.append(cell)
    return resource_tiles

def get_units_on_stack(units, game_map):
    units_on_stack: list[Unit] = []
    unit_positions: list[Position] = []
    for unit in units:
        if(unit.pos in unit_positions and game_map.get_cell_by_pos(unit.pos).citytile):
            units_on_stack.append(unit)
        else:
            unit_positions.append(unit.pos)
    return units_on_stack


def get_max_unit_count(unit_type, turn):
    level = (int(turn/40)+1)*40
    max_unit_count = LEVEL_TO_UNITS[str(level)]
    return max_unit_count[unit_type]

def get_workers_count(units):
    workers = 0
    for unit in units:
        if(unit.is_worker):
            workers += 1
    return workers

def is_workers_off_time(turn):
    params = GAME_CONSTANTS["PARAMETERS"]
    turns_to_newday = params["NIGHT_LENGTH"]+params["DAY_LENGTH"]-(turn%(params["NIGHT_LENGTH"]+params["DAY_LENGTH"]))
    if(turns_to_newday<=(params["NIGHT_LENGTH"]+EVENING_LENGTH)):
        return True
    else:
        return False

def return_to_city(cities, unit):
    if len(cities) > 0:
        closest_dist = math.inf
        closest_city_tile = None
        for k, city in cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(unit.pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
        if closest_city_tile is not None:
            move_dir = unit.pos.direction_to(closest_city_tile.pos)
            return move_dir

def get_fuel_earn_rate_map(height, width, constants, coal_researched, uranium_researched):
    collection_rate = constants["PARAMETERS"]["WORKER_COLLECTION_RATE"]
    fuel_value_rate = constants["PARAMETERS"]["RESOURCE_TO_FUEL_RATE"]
    fuel_earn_rate_map = [[0 for x in range(height)] for y in range(width)] 
    for y in range(height):
        for x in range(width):
            c_cell = game_state.map.get_cell(x, y)
            w_cell = game_state.map.get_cell(x-1, y) if x>0 else None
            n_cell = game_state.map.get_cell(x, y-1) if y>0 else None
            e_cell = game_state.map.get_cell(x+1, y) if x<width-1 else None
            s_cell = game_state.map.get_cell(x, y+1) if y<height-1 else None

            cells = [c_cell, w_cell, n_cell, e_cell, s_cell]
            fuel_earn_rate = 0
            for cell in cells:
                if cell and cell.has_resource():
                    if(cell.resource.type == 'wood'):
                        fuel_earn_rate += fuel_value_rate["WOOD"] * collection_rate["WOOD"]
                    elif(cell.resource.type == 'coal' and coal_researched):
                        fuel_earn_rate += fuel_value_rate["COAL"] * collection_rate["COAL"]
                    elif(cell.resource.type == 'uranium' and uranium_researched):
                        fuel_earn_rate += fuel_value_rate["URANIUM"] * collection_rate["URANIUM"]
            fuel_earn_rate_map[y][x] = fuel_earn_rate
    return fuel_earn_rate_map


def get_fuel_earnable_tiles(width, height, fuel_earn_rate_map):
    fuel_earnable_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            if(fuel_earn_rate_map[y][x]>0):
                fuel_earnable_tiles.append(game_state.map.get_cell(x, y))
    return fuel_earnable_tiles

def get_adjacent_cells(pos, width, height):
    x = pos.x
    y = pos.y
    cell_dict = {
        "n": None,
        "e": None,
        "s": None,
        "w": None,
        "c": None,
                }
    cell_dict["w"] = game_state.map.get_cell(x-1, y) if x>0 else None
    cell_dict["n"]  = game_state.map.get_cell(x, y-1) if y>0 else None
    cell_dict["e"]  = game_state.map.get_cell(x+1, y) if x<width-1 else None
    cell_dict["s"]  = game_state.map.get_cell(x, y+1) if y<height-1 else None
    cell_dict["c"]  = game_state.map.get_cell(x, y)

    return cell_dict

def validate_move(pos, direction, opponent_team, height, width) -> bool:
    cell_dict = get_adjacent_cells(pos, width, height)
    d_cell = cell_dict[direction]
    
    if(d_cell.citytile):
        if(d_cell.citytile.team == opponent_team):
            return False
        else:
            return True
    else:
        return True


def get_closest_tile(tiles,unit):
    closest_dist = math.inf
    closest_tile = None
    for tile in tiles:
        dist = tile.pos.distance_to(unit.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_tile = tile
    return closest_tile

    
def get_best_tile(tiles,unit, score_map, turn):
    best_score = 0
    economy_tiles = []
    params = GAME_CONSTANTS["PARAMETERS"]
    for tile in tiles:
        score = score_map[tile.pos.y][tile.pos.x]
        if score > best_score:
            best_score = score
            economy_tiles = [tile]
        if score == best_score:
            economy_tiles.append(tile)
    turns_to_night = params["DAY_LENGTH"]-(turn%(params["NIGHT_LENGTH"]+params["DAY_LENGTH"]))
    best_tiles = []
    for tile in economy_tiles:
        distance = tile.pos.distance_to(unit.pos)
        if(distance <turns_to_night/2):
            best_tiles.append(tile)
    if(len(best_tiles)>0):
        best_tile = get_closest_tile(best_tiles, unit)
    else:
        best_tile = get_closest_tile(tiles, unit)
    return best_tile


def get_light_upkeep_ability(turn, player):
    params = GAME_CONSTANTS["PARAMETERS"]
    fuel_cost_per_day = 0
    fuel_remaining = 0
    for city_name in player.cities.keys():
        city = player.cities[city_name]
        fuel_cost_per_day += city.get_light_upkeep()
        fuel_remaining += city.fuel
    for unit in player.units:
        if unit.is_worker():
            fuel_cost_per_day += params['LIGHT_UPKEEP']['WORKER']
        else:
            fuel_cost_per_day += params['LIGHT_UPKEEP']['CART']
    
    # remaining_night_turns = get_remaining_night_turns(turn)

    fuel_cost = params["NIGHT_LENGTH"]* fuel_cost_per_day
    if(fuel_cost>fuel_remaining):
        return False
    else:
        return True

def get_remaining_night_turns(turn):
    params = GAME_CONSTANTS["PARAMETERS"]
    turns_per_day = params["NIGHT_LENGTH"]+params["DAY_LENGTH"]
    night_turns_in_day = turn%turns_per_day - params["DAY_LENGTH"]
    night_turns = 0
    if(night_turns_in_day>0):
        night_turns += night_turns_in_day
    else:
        night_turns += params["NIGHT_LENGTH"]
    
    night_turns += params["NIGHT_LENGTH"]* (int(params["MAX_DAYS"]/turns_per_day)-int(turn/turns_per_day))

    return night_turns

def get_closest_city_tile(unit, player):
    cities = list(player.cities.keys())
    distance = math.inf
    closest_city_tile = None
    for city in cities:
        city_tiles = player.cities[city].citytiles
        for city_tile in city_tiles:
            if(city_tile.pos.distance_to(unit.pos)<distance):
                distance = city_tile.pos.distance_to(unit.pos)
                closest_city_tile = city_tile
    return closest_city_tile

def is_pos_adjecent_to_city(pos, cities):
    for city_name in cities.keys():
        city_tiles = cities[city_name].citytiles
        for city_tile in city_tiles:
            if city_tile.pos.is_adjacent(pos):
                return True
    return False


def get_closest_resource_tiles(unit, width, height, coal_researched, uranium_researched):
    tiles = get_resource_tiles(width, height, coal_researched, uranium_researched)
    sorted_tiles = []
    while len(tiles):
        closest_tile = get_closest_tile(tiles,unit)
        sorted_tiles.append(closest_tile)
        tiles.remove(closest_tile)
    return sorted_tiles

def total_city_tiles(cities):
    count = 0
    for city_name in cities.keys():
        city_tiles = cities[city_name].citytiles
        count += len(city_tiles)
    return count

def get_validated_moves(moves, direct_dic, width, height):
    validated_moves = []
    unit_positions = []
    for move in moves:
        if(move['direction'] == 'c'): 
            x = move['unit'].pos.x
            y = move['unit'].pos.y
        elif(move['direction'] == 'n'): 
            x = move['unit'].pos.x
            y = move['unit'].pos.y - 1
        elif(move['direction'] == 'e'): 
            x = move['unit'].pos.x + 1
            y = move['unit'].pos.y
        elif(move['direction'] == 's'): 
            x = move['unit'].pos.x
            y = move['unit'].pos.y + 1
        elif(move['direction'] == 'w'): 
            x = move['unit'].pos.x - 1
            y = move['unit'].pos.y
        
        pos = "{}_{}".format(x,y)
        if(pos not in unit_positions):
            unit_positions.append(pos)
            validated_moves.append(move)
        else:
            move['direction'] = get_random_direction(move['unit'].pos, direct_dic, width, height)
            validated_moves.append(move)
    return validated_moves


def is_pos_adjecent_to_resource(pos, resource_tiles):
    for tile in resource_tiles:
        if tile.pos.is_adjacent(pos):
            return True
    return False


def get_unit_moves(units, game_state, width, height, player, opponent, unit_team):
    units_on_stack = get_units_on_stack(units, game_state.map)
    resource_tiles = get_resource_tiles(width, height, player.researched_coal(), player.researched_uranium())
    annotations = []
    moves = []
    builds = []
    for unit in units:
        if unit.is_worker() and unit.can_act():
            cell = game_state.map.get_cell_by_pos(unit.pos)
            if(is_pos_adjecent_to_resource(unit.pos, resource_tiles) and not cell.citytile and unit.can_build(game_state.map) and get_light_upkeep_ability(game_state.turn, player)):
                builds.append(unit.build_city())
                annotations.append(annotate.sidetext("build city" + str(unit.id)))
                moves.append({"unit": unit, "direction": "c"})
            elif(unit.cargo.wood+unit.cargo.coal+unit.cargo.uranium >= 100):
                tile = get_closest_city_tile(unit, player)
                directions = [DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST]
                if (tile):
                    if(tile.pos.distance_to(unit.pos) < 5):
                        adjacent_cells = get_adjacent_cells(tile.pos, width, height)
                        for direction in directions:
                            if adjacent_cells[direction] and not adjacent_cells[direction].citytile and not adjacent_cells[direction].resource:
                                move = unit.pos.direction_to(adjacent_cells[direction].pos)
                                if validate_move(unit.pos, move, opponent.team, height, width):
                                    if(move!='c'):
                                        moves.append({"unit": unit, "direction": move})
                                        annotations.append(annotate.sidetext("go to build {} {} {} {}".format(unit.id, move, adjacent_cells[direction].pos.x, adjacent_cells[direction].pos.y)))
                                    else:
                                        tile = get_closest_city_tile(unit, player)
                                        move = unit.pos.direction_to(tile.pos)
                                        moves.append({"unit": unit, "direction": move})
                                else:
                                    if unit.can_build(game_state.map):
                                        annotations.append(annotate.sidetext("go to build" + str(unit.id) + str(move)))
                                        moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
                                    else:
                                        tile = get_closest_city_tile(unit, player)
                                        move = unit.pos.direction_to(tile.pos)
                                        moves.append({"unit": unit, "direction": move})
                    elif unit.can_build(game_state.map):
                        builds.append(unit.build_city())
                        annotations.append(annotate.sidetext("build city" + str(unit.id)))
                        moves.append({"unit": unit, "direction": "c"})
                    else:
                        move = get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)
                        if validate_move(unit.pos, move, opponent.team, height, width):
                            moves.append({"unit": unit, "direction": move})
                            annotations.append(annotate.sidetext("on stack random" + str(unit.id) + str(move)))
                        else:
                            annotations.append(annotate.sidetext("on stack random" + str(unit.id) + str(move)))
                            moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
            elif(unit in units_on_stack):
                move = get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)
                if validate_move(unit.pos, move, opponent.team, height, width):
                    moves.append({"unit": unit, "direction": move})
                    annotations.append(annotate.sidetext("on stack random" + str(unit.id) + str(move)))
                else:
                    annotations.append(annotate.sidetext("on stack random" + str(unit.id) + str(move)))
                    moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
            elif (is_workers_off_time(game_state.turn)):
                return_to_city_dir = return_to_city(player.cities, unit)
                if(return_to_city_dir is not None):
                    move = return_to_city_dir
                    if validate_move(unit.pos, move, opponent.team, height, width):
                        annotations.append(annotate.sidetext("going home normal" + str(unit.id) + str(move)))
                        moves.append({"unit": unit, "direction": move})
                    else:
                        annotations.append(annotate.sidetext("going home random" + str(unit.id) + str(move)))
                        moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
            elif unit.get_cargo_space_left() > 0:
                closest_resource_tiles = get_closest_resource_tiles(unit, width, height, player.researched_coal(), player.researched_uranium())
                if unit_team%2:
                    best_tile = closest_resource_tiles[0]
                else:
                    best_tile = closest_resource_tiles[1]
                
                if(best_tile):
                    move = unit.pos.direction_to(best_tile.pos)
                    annotations.append(annotate.circle(best_tile.pos.x, best_tile.pos.y))
                else:
                    move = None
                
                if move and validate_move(unit.pos, move, opponent.team, height, width):
                    annotations.append(annotate.sidetext("cargo left normal" + str(unit.id) + str(move)))
                    moves.append({"unit": unit, "direction": move})
                else:
                    annotations.append(annotate.sidetext("cargo left random" + str(unit.id) + str(move)))
                    moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                return_to_city_dir = return_to_city(player.cities, unit)
                if(return_to_city_dir is not None):
                    move = return_to_city_dir
                    if validate_move(unit.pos, move, opponent.team, height, width):
                        annotations.append(annotate.sidetext("else normal" + str(unit.id) + str(move)))
                        moves.append({"unit": unit, "direction": move})
                    else:
                        annotations.append(annotate.sidetext("else random" + str(unit.id) + str(move)))
                        moves.append({"unit": unit, "direction": get_random_direction(unit.pos, GAME_CONSTANTS['DIRECTIONS'], width, height)})
        else:
            annotations.append(annotate.sidetext("cooldown" + str(unit.id)))
            moves.append({"unit": unit, "direction": "c"})
    return moves, builds, annotations

def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []
    
    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    # fuel_earn_rate_map = get_fuel_earn_rate_map(height, width, GAME_CONSTANTS, player.researched_coal(), player.researched_uranium())
    # fuel_earnable_tiles = get_fuel_earnable_tiles(width, height, fuel_earn_rate_map)

    # we iterate over all our units and do something with them
    unit_teams = []
    if len(player.units)>2:
        middle = int(len(player.units)/2)
        unit_teams.append(player.units[:middle])
        unit_teams.append(player.units[middle:])
    else:
        unit_teams.append(player.units)
    
    for units in unit_teams:
        moves, builds, annotations = get_unit_moves(units, game_state, width, height, player, opponent, unit_teams.index(units))
        for move in get_validated_moves(moves,  GAME_CONSTANTS['DIRECTIONS'], width, height):
            if (move["direction"] != "c"):
                actions.append(move["unit"].move(move["direction"]))
        actions.extend(builds)
        actions.extend(annotations)
    
    # we iterate over all our units and do something with them
    cities = list(player.cities.keys())

    for city in cities:
        city_tiles = player.cities[city].citytiles
        for city_tile in city_tiles:
            if (city_tile.can_act()):   
                workers_count = get_workers_count(player.units)
                carts_count = len(player.units) - get_workers_count(player.units)
                
                if(workers_count < get_max_unit_count("workers", game_state.turn) and len(player.units) < total_city_tiles(player.cities)):
                    actions.append(city_tile.build_worker())
                elif(player.research_points < get_max_unit_count("research", game_state.turn)):
                    actions.append(city_tile.research())
                elif(carts_count < get_max_unit_count("carts", game_state.turn)):
                    actions.append(city_tile.build_cart())
    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    return actions
