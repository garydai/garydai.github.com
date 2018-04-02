import Cookies from 'js-cookie'

const TokenKey = 'Admin-Token'

export function getToken() {
  return JSON.parse(Cookies.get(TokenKey))
}

export function setToken(token) {
  return Cookies.set(TokenKey, token)
}

export function removeToken() {
  return Cookies.remove(TokenKey)
}
