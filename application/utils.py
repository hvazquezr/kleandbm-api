from typing import Optional 

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer

from application.config import get_settings

class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status.HTTP_403_FORBIDDEN, detail=detail)

class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )


class VerifyToken:
    """Does all the token verification using PyJWT"""

    def __init__(self):
        self.config = get_settings()

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f'https://{self.config.auth0_domain}/.well-known/jwks.json'
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    async def verify(self,
                     security_scopes: SecurityScopes,
                     token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer())
                     ):
        if token is None:
            raise UnauthenticatedException

        # This gets the 'kid' from the passed token
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(
                token.credentials
            ).key
        except jwt.exceptions.PyJWKClientError as error:
            raise UnauthorizedException(str(error))
        except jwt.exceptions.DecodeError as error:
            raise UnauthorizedException(str(error))

        try:
            payload = jwt.decode(
                token.credentials,
                signing_key,
                algorithms=self.config.auth0_algorithms,
                audience=self.config.auth0_api_audience,
                issuer=self.config.auth0_issuer,
            )
        except Exception as error:
            raise UnauthorizedException(str(error))
    
        return payload

def remove_attributes(json_array, attributes_to_remove):

    # Iterate through each element in the JSON array
    cleaned_array = []
    for item in json_array:
        # Create a new dictionary with only the desired attributes
        cleaned_item = {key: value for key, value in item.items() if key not in attributes_to_remove}

        # Remove attributes from the 'columns' array if it exists
        if 'columns' in cleaned_item and isinstance(cleaned_item['columns'], list):
            cleaned_item['columns'] = [{col_key: col_value for col_key, col_value in col.items() if col_key not in attributes_to_remove} for col in cleaned_item['columns']]

        cleaned_array.append(cleaned_item)

    return cleaned_array