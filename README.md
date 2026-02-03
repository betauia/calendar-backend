
# Calendar sync tool | BetaDev

The main purpose of this tool is to synchronize calendar events across third-party vendors in a clean, loosely coupled and interchangeable way. The project is intended for internal usage by BetaDev.
## Basic implementation overview
The backend is made using python and fastApi. The backend server works as the main synchronizer and ground truth for all calendar events and constantly tries to keep track of and synchronize events across its connected clients. The backend is a RESTful api meaning that external clients can connect to it and implement their own synchronization logic per third-party service. This allows decoupled and maintainable development over time.
## Project focus

The main focus of this project is interchangeability and modifiability. The backend must be extendable in a way that makes it easy to extend support for future third-party vendors. 

In order for future contributers to understand the system and make use of its modifiability, sufficient documentation will be necessary and an important aspect to make long term maintainability possible.
## Contributing

Contributions are always welcome and we especially encourage curious BetaDev members to engage themselves in the project. As of now the project is still in very early development, and the project foundation is still being laid out. You can expect more github issues and easier contribution in the near future.