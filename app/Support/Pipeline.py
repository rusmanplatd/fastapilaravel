from __future__ import annotations

from typing import Any, List, Callable, TypeVar, Union
from functools import reduce

T = TypeVar('T')


class Pipeline:
    """Laravel-style Pipeline for processing data through multiple stages."""
    
    def __init__(self, passable: Any) -> None:
        self.passable = passable
        self.pipes: List[Union[Callable[[Any, Callable[[Any], Any]], Any], str]] = []
        self.method = "handle"
    
    def send(self, passable: Any) -> Pipeline:
        """Set the object being sent through the pipeline."""
        self.passable = passable
        return self
    
    def through(self, pipes: List[Union[Callable[..., Any], str]]) -> Pipeline:
        """Set the array of pipes."""
        self.pipes = pipes
        return self
    
    def via(self, method: str) -> Pipeline:
        """Set the method to call on pipes."""
        self.method = method
        return self
    
    def then(self, destination: Callable[[Any], T]) -> T:
        """Run the pipeline with a final destination."""
        pipeline = reduce(
            lambda stack, pipe: self._carry(pipe, stack),
            reversed(self.pipes),
            destination
        )
        
        return pipeline(self.passable)
    
    def then_return(self) -> Any:
        """Run the pipeline and return the result."""
        return self.then(lambda passable: passable)
    
    def _carry(self, pipe: Union[Callable[..., Any], str], stack: Callable[[Any], Any]) -> Callable[[Any], Any]:
        """Get a closure that represents a slice of the application onion."""
        def closure(passable: Any) -> Any:
            if callable(pipe):
                # If pipe is a callable, call it directly
                return pipe(passable, stack)
            elif isinstance(pipe, str):
                # If pipe is a string, try to resolve it
                # This would need proper class resolution in a real implementation
                return stack(passable)
            elif hasattr(pipe, self.method):
                # If pipe is an object with the specified method
                method = getattr(pipe, self.method)
                if callable(method):
                    return method(passable, stack)
            
            return stack(passable)
        
        return closure


def pipeline(passable: Any) -> Pipeline:
    """Helper function to create a pipeline."""
    return Pipeline(passable)