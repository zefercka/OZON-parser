import re


def get_id_from_url(url: str) -> int:
    """Get the id from a url."""
    
    id_ = int(re.sub(r"\D", '', url.split('-')[-1]))
    
    return id_