cmake_minimum_required (VERSION 3.5)
project (_pyopcode)

set(Boost_USE_STATIC_LIBS OFF)
set(Boost_USE_MULTITHREADED ON)
find_package(Boost COMPONENTS python3 REQUIRED)
message("Include dirs of boost: " ${Boost_INCLUDE_DIRS} )
message("Libs of boost: " ${Boost_LIBRARIES} )

find_package(PythonLibs REQUIRED)
message("Include dirs of Python: " ${PYTHON_INCLUDE_DIRS} )
message("Libs of Python: " ${PYTHON_LIBRARIES} )


file(GLOB OPCODE_SOURCE opcode/*.cpp)
file(GLOB ICE_SOURCE opcode/Ice/*.cpp)

include_directories(opcode)
include_directories(opcode/Ice)

include_directories(${PYTHON_INCLUDE_DIRS})
include_directories(${NUMPY_INCLUDE_DIR})
include_directories(${Boost_INCLUDE_DIR})

LINK_DIRECTORIES(${PYTHON_LIBRARIES})
LINK_DIRECTORIES(${Boost_LIBRARIES})


ADD_LIBRARY(${PROJECT_NAME} MODULE interface.cpp ${OPCODE_SOURCE} ${ICE_SOURCE})
if( WIN32 )
    SET_TARGET_PROPERTIES(${PROJECT_NAME} PROPERTIES SUFFIX ".pyd")
else()
    SET_TARGET_PROPERTIES(${PROJECT_NAME} PROPERTIES SUFFIX ".so")
endif()


target_compile_definitions(${PROJECT_NAME} PUBLIC ICE_NO_DLL BAN_OPCODE_AUTOLINK)

TARGET_LINK_LIBRARIES(${PROJECT_NAME}
    ${Boost_LIBRARIES}
    ${PYTHON_LIBRARIES}
    )
