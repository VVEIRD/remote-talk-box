def is_int(var:str):
    '''Check if the given string contains an integer'''
    try:
        # try converting to integer
        int(var)
    except ValueError:
        return False
    return True