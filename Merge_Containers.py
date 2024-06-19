import typing as tp


#A method to check if an object is made of elements of its own type 
# up to some predefined depth so as to not recurse forever.  
# This function will help us avoid infinitely recursing on strings 
def is_fractal(iterable, max_depth: int, depth: int = 0)->bool: 
    if depth == max_depth: 
        try: 
            return type(next(iter(iterable))) == type(iterable) 
        except Exception as err: pass 
        return False 
    
    try: 
        if type(next(iter(iterable))) == type(iterable): 
            return is_fractal(next(iter(iterable)), max_depth, depth + 1) 
    except Exception as err: pass 
    return False 

#A method to determine the practical base type(set, list, dict, value)
# of an object 
def get_basic_type(obj, fractal_check_depth: int = 9, known_fractals: tuple[type] = (str, ))->tp.Literal['set-like', 'list-like', 'dict-like', 'value']: 
    try: #Check for dict-likeness 
        if not isinstance(obj, dict): 
            x = obj.keys()
        return 'dict-like' 
    except Exception as err: 
        try: #Check for list-likeness 
            if not isinstance(obj, list): 
                x = obj[0] 
                #Only non-fractal int-indexed iterables can be considered lists.
                #Otherwise, it's just an iterable simple value(like a string) 
                if type(obj) in known_fractals \
                or is_fractal(obj, fractal_check_depth):  
                    return 'value' 
            return 'list-like' 
        except Exception as err: 
            try: #Check for set-likeness 
                x = iter(obj) 
                return 'set-like' 
            except Exception as err: 
                pass  
    
    return 'value' 

class StopMerge(Exception): pass

#Combine the contents of 2 containers. The containers should mostly have the same basic
# structure at all levels e.g. list merge with lists, dicts merge with dicts.
# It is acceptable for value-types on the rhs to be merged into containers on the lhs except in the case of a dict-like.
# This function expects containers/objects that are either:
#  - like lists(int-indexed, has append and insert methods with effectively the same parameters)
#  - like dicts(key-indexed, has keys method with effectively the same parameters)
#  - like sets(iterable, has add method with effectively the same parameters)
#  - values(not like any containers); for values, if a merge function isn't provided, they are added to the lhs container
# Merging between a container and a value results in the value being added to the container
# This function does in-place modification of the `lhs`
def merge( 
    lhs, rhs, #lhs: what is merged into, rhs: where data for the merge comes from
    stop_on: set[tuple[type, int]] = {}, #Certain lhs types at certain recursion depths where merging should stop
    types_to_mergers: dict[tuple[type, type], tp.Callable[[tp.Any, tp.Any], tp.Any]] = {}, #A dict mapping 2-tuples of types to associated custom merge functions
    known_fractals: tuple[type] = (str, ), #Fractals are data types that always yield their own type upon iteration
    fractal_check_depth: int = 9, #Max depth of sameness before a value is called a fractal
    depth = 0 #Recursion depth, not meant to be passed
): 
    #Stop merging if the depth and lhs type match a pair in `stop_on`
    if (type(lhs), depth) in stop_on:
        raise StopMerge()

    #Determine data structure of lhs and rhs 
    lhs_basic_type = get_basic_type(lhs, fractal_check_depth, known_fractals)
    rhs_basic_type = get_basic_type(rhs, fractal_check_depth, known_fractals)

    #Merge
    # Simple value merged with other
    if lhs_basic_type == 'value': 
        #Use the custom merging function for these types if it is present  
        true_types = (type(lhs), type(rhs)) 
        if true_types in types_to_mergers: 
            return types_to_mergers[true_types](lhs, rhs) 

        #Raise error to indicate that there is no merge for these objects 
        # or to stop the merging for the previous recursive call(indicated by `depth >= 1`)
        if depth < 1:
            raise ValueError(f"No merge behavior provided for types {true_types[0]} and {true_types[1]}")
        raise StopMerge()

    # In other cases, merge into lhs
    #  Set-like merged with set-like or value
    elif lhs_basic_type == 'set-like': 
        if rhs_basic_type == 'value': #Add value to container
            lhs.add(rhs)
            
        else: #Merge containers
            for item in rhs: 
                lhs.add(item)

    #  List-like merged with list-like or value
    elif lhs_basic_type == 'list-like': 
        if rhs_basic_type == 'value': #Add value to container
            lhs.append(rhs)
            
        else: #Merge containers
            #Merge common indexes 
            lhs_idx = 0
            rhs_idx = 0
            while lhs_idx < len(lhs): 
                if rhs_idx >= len(rhs):  
                    break 
                try: 
                    lhs[lhs_idx] = merge( 
                        lhs[lhs_idx], rhs[rhs_idx], stop_on,
                        types_to_mergers, 
                        known_fractals, fractal_check_depth,
                        depth + 1
                    ) 
                except StopMerge as err:
                    lhs.insert(lhs_idx + 1, rhs[rhs_idx]) 
                    lhs_idx += 1
                lhs_idx += 1
                rhs_idx += 1
    
            for i in range(rhs_idx, len(rhs)): #Add new(higher) indexes from rhs
                lhs.append(rhs[i]) 

    #  Dict-like merged with dict-like 
    else:
        if rhs_basic_type == 'value': #No concrete way to add value to dict
            raise ValueError(f"Cannot merge basic types 'dict-like' and 'value' (lhs={lhs}, rhs={rhs})") 
            
        else: #Merge containers
            for key in lhs: #Merge values with common keys
                if key not in rhs: 
                    continue 
                try: 
                    lhs[key] = merge( 
                        lhs[key], rhs[key], stop_on, 
                        types_to_mergers, 
                        known_fractals, fractal_check_depth,
                        depth + 1
                    )
                except StopMerge as err: 
                    lhs[key] = [lhs[key], rhs[key]]
    
            for key in rhs: #Add new keys from rhs
                if key not in lhs: 
                    lhs[key] = rhs[key] 
                
    return lhs 
